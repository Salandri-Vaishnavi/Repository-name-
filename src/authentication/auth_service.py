
import re
import sqlite3

import bcrypt

from src.database.connection import get_connection


class AuthenticationError(Exception):
    """Raised when an authentication operation fails."""


def validate_registration(username, email, password, full_name=None):
    """Validate registration details."""

    if not all(isinstance(value, str) for value in (
        username, email, password
    )):
        raise ValueError("Username, email and password are required.")

    username = username.strip()
    email = email.strip().lower()

    if not re.fullmatch(r"[A-Za-z0-9_]{3,30}", username):
        raise ValueError(
            "Username must contain 3-30 characters "
            "using letters, numbers or underscores."
        )

    if not re.fullmatch(
        r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
        email
    ):
        raise ValueError("Please enter a valid email address.")

    if len(password.encode("utf-8")) < 8:
        raise ValueError("Password must contain at least 8 bytes.")

    if len(password.encode("utf-8")) > 72:
        raise ValueError("Password must not exceed 72 bytes.")

    if full_name is not None:
        if not isinstance(full_name, str):
            raise ValueError("Full name must be text.")

        full_name = full_name.strip()

        if len(full_name) > 100:
            raise ValueError("Full name must not exceed 100 characters.")

        if not full_name:
            full_name = None

    return username, email, password, full_name


def _public_user(user):
    """Return safe user information without the password hash."""

    if user is None:
        return None

    return {
        "user_id": user["user_id"],
        "username": user["username"],
        "email": user["email"],
        "full_name": user["full_name"],
        "created_at": user["created_at"]
    }


def register_user(username, email, password, full_name=None):
    """Register a new CineMatch AI user."""

    username, email, password, full_name = validate_registration(
        username,
        email,
        password,
        full_name
    )

    password_hash = bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt(rounds=12)
    ).decode("utf-8")

    try:
        with get_connection() as connection:

            cursor = connection.execute(
                """
                INSERT INTO users (
                    username,
                    email,
                    password_hash,
                    full_name
                )
                VALUES (?, ?, ?, ?)
                """,
                (
                    username,
                    email,
                    password_hash,
                    full_name
                )
            )

            user = connection.execute(
                """
                SELECT user_id, username, email,
                       full_name, created_at
                FROM users
                WHERE user_id = ?
                """,
                (cursor.lastrowid,)
            ).fetchone()

            connection.execute(
                """
                INSERT INTO user_preferences (user_id)
                VALUES (?)
                """,
                (user["user_id"],)
            )

            return _public_user(user)

    except sqlite3.IntegrityError as error:
        raise AuthenticationError(
            "Username or email already exists."
        ) from error


def authenticate_user(identifier, password):
    """Authenticate using username or email."""

    if (
        not isinstance(identifier, str)
        or not identifier.strip()
        or not isinstance(password, str)
        or not password
    ):
        return None

    if len(password.encode("utf-8")) > 72:
        return None

    identifier = identifier.strip()

    with get_connection() as connection:

        user = connection.execute(
            """
            SELECT user_id, username, email,
                   password_hash, full_name,
                   created_at, is_active
            FROM users
            WHERE username = ? COLLATE NOCASE
               OR email = ? COLLATE NOCASE
            """,
            (identifier, identifier)
        ).fetchone()

        if user is None or user["is_active"] != 1:
            return None

        try:
            password_matches = bcrypt.checkpw(
                password.encode("utf-8"),
                user["password_hash"].encode("utf-8")
            )
        except (ValueError, TypeError):
            return None

        if not password_matches:
            return None

        return _public_user(user)


def get_user_by_id(user_id):
    """Retrieve an active user's public profile."""

    if isinstance(user_id, bool) or not isinstance(user_id, int):
        raise ValueError("User ID must be an integer.")

    if user_id < 1:
        raise ValueError("User ID must be positive.")

    with get_connection() as connection:

        user = connection.execute(
            """
            SELECT user_id, username, email,
                   full_name, created_at
            FROM users
            WHERE user_id = ?
              AND is_active = 1
            """,
            (user_id,)
        ).fetchone()

        return _public_user(user)
