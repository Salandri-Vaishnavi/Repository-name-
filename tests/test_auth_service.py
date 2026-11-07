
import sqlite3
from contextlib import contextmanager

import bcrypt
import pytest

from src.authentication import auth_service
from src.database import schema


@pytest.fixture
def test_database(tmp_path, monkeypatch):
    """Create an isolated temporary database for each test."""

    database_file = tmp_path / "test_cinematch.db"

    @contextmanager
    def temporary_connection():
        connection = sqlite3.connect(database_file, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")

        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    monkeypatch.setattr(
        auth_service, "get_connection", temporary_connection
    )
    monkeypatch.setattr(
        schema, "get_connection", temporary_connection
    )

    schema.create_tables()

    return database_file


def test_user_registration(test_database):
    user = auth_service.register_user(
        "vaishu123",
        "vaishu@example.com",
        "StrongPass123",
        "Vaishnavi"
    )

    assert user["username"] == "vaishu123"
    assert user["email"] == "vaishu@example.com"
    assert user["full_name"] == "Vaishnavi"
    assert "password_hash" not in user


def test_user_preferences_created_after_registration(test_database):
    user = auth_service.register_user(
        "movieuser",
        "movie@example.com",
        "StrongPass123"
    )

    with auth_service.get_connection() as connection:
        preferences = connection.execute(
            """
            SELECT user_id, preferred_language
            FROM user_preferences
            WHERE user_id = ?
            """,
            (user["user_id"],)
        ).fetchone()

    assert preferences is not None
    assert preferences["preferred_language"] == "English"


def test_password_is_hashed(test_database):
    password = "StrongPass123"

    user = auth_service.register_user(
        "hashuser",
        "hash@example.com",
        password
    )

    with auth_service.get_connection() as connection:
        stored_user = connection.execute(
            """
            SELECT password_hash
            FROM users
            WHERE user_id = ?
            """,
            (user["user_id"],)
        ).fetchone()

    password_hash = stored_user["password_hash"]

    assert password_hash != password
    assert bcrypt.checkpw(
        password.encode("utf-8"),
        password_hash.encode("utf-8")
    )


def test_login_with_username(test_database):
    auth_service.register_user(
        "loginuser",
        "login@example.com",
        "StrongPass123"
    )

    user = auth_service.authenticate_user(
        "loginuser",
        "StrongPass123"
    )

    assert user is not None
    assert user["username"] == "loginuser"


def test_login_with_email(test_database):
    auth_service.register_user(
        "emailuser",
        "email@example.com",
        "StrongPass123"
    )

    user = auth_service.authenticate_user(
        "email@example.com",
        "StrongPass123"
    )

    assert user is not None
    assert user["email"] == "email@example.com"


def test_login_rejects_incorrect_password(test_database):
    auth_service.register_user(
        "wrongpass",
        "wrong@example.com",
        "StrongPass123"
    )

    user = auth_service.authenticate_user(
        "wrongpass",
        "IncorrectPass123"
    )

    assert user is None


def test_login_rejects_unknown_user(test_database):
    user = auth_service.authenticate_user(
        "unknownuser",
        "StrongPass123"
    )

    assert user is None


def test_duplicate_username_is_rejected(test_database):
    auth_service.register_user(
        "duplicate",
        "first@example.com",
        "StrongPass123"
    )

    with pytest.raises(
        auth_service.AuthenticationError,
        match="already exists"
    ):
        auth_service.register_user(
            "duplicate",
            "second@example.com",
            "AnotherPass123"
        )


def test_duplicate_email_is_rejected(test_database):
    auth_service.register_user(
        "firstuser",
        "duplicate@example.com",
        "StrongPass123"
    )

    with pytest.raises(
        auth_service.AuthenticationError,
        match="already exists"
    ):
        auth_service.register_user(
            "seconduser",
            "duplicate@example.com",
            "AnotherPass123"
        )


@pytest.mark.parametrize(
    "username,email,password",
    [
        ("ab", "valid@example.com", "StrongPass123"),
        ("validuser", "invalid-email", "StrongPass123"),
        ("validuser", "valid@example.com", "short"),
        ("validuser", "valid@example.com", "x" * 73),
    ]
)
def test_invalid_registration_details_are_rejected(
    test_database, username, email, password
):
    with pytest.raises(ValueError):
        auth_service.register_user(username, email, password)


def test_inactive_user_cannot_login(test_database):
    user = auth_service.register_user(
        "inactiveuser",
        "inactive@example.com",
        "StrongPass123"
    )

    with auth_service.get_connection() as connection:
        connection.execute(
            """
            UPDATE users
            SET is_active = 0
            WHERE user_id = ?
            """,
            (user["user_id"],)
        )

    result = auth_service.authenticate_user(
        "inactiveuser",
        "StrongPass123"
    )

    assert result is None


def test_get_user_by_id(test_database):
    registered_user = auth_service.register_user(
        "profileuser",
        "profile@example.com",
        "StrongPass123",
        "Profile User"
    )

    user = auth_service.get_user_by_id(
        registered_user["user_id"]
    )

    assert user is not None
    assert user["username"] == "profileuser"
    assert user["full_name"] == "Profile User"
    assert "password_hash" not in user


def test_get_user_by_id_returns_none_for_unknown_user(test_database):
    assert auth_service.get_user_by_id(9999) is None


@pytest.mark.parametrize("invalid_id", [0, -1, True, "1", 1.5])
def test_get_user_by_id_rejects_invalid_id(test_database, invalid_id):
    with pytest.raises(ValueError):
        auth_service.get_user_by_id(invalid_id)
