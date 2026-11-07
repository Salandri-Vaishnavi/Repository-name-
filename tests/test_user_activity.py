
import sqlite3
from contextlib import contextmanager

import pytest

from src.database import schema, user_activity


@pytest.fixture
def test_database(tmp_path, monkeypatch):
    """Create an isolated database for each activity test."""

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
        user_activity, "get_connection", temporary_connection
    )
    monkeypatch.setattr(
        schema, "get_connection", temporary_connection
    )

    schema.create_tables()

    with temporary_connection() as connection:
        connection.executemany(
            """
            INSERT INTO users (
                user_id, username, email, password_hash, full_name
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            [
                (1, "userone", "one@example.com", "hash1", "User One"),
                (2, "usertwo", "two@example.com", "hash2", "User Two"),
            ]
        )

        connection.executemany(
            """
            INSERT INTO movies (
                movie_id, title, release_year, genres,
                average_rating, rating_count
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [
                (101, "Test Movie One", 2020, "Action|Sci-Fi", 4.2, 100),
                (102, "Test Movie Two", 2022, "Comedy|Drama", 3.8, 50),
            ]
        )

    return database_file


# ---------------- WATCHLIST TESTS ----------------

def test_add_to_watchlist(test_database):
    assert user_activity.add_to_watchlist(1, 101) is True


def test_duplicate_watchlist_entry_is_prevented(test_database):
    assert user_activity.add_to_watchlist(1, 101) is True
    assert user_activity.add_to_watchlist(1, 101) is False

    assert len(user_activity.get_watchlist(1)) == 1


def test_get_watchlist_returns_movie_details(test_database):
    user_activity.add_to_watchlist(1, 101)

    watchlist = user_activity.get_watchlist(1)

    assert len(watchlist) == 1
    assert watchlist[0]["movie_id"] == 101
    assert watchlist[0]["title"] == "Test Movie One"


def test_watchlist_is_user_specific(test_database):
    user_activity.add_to_watchlist(1, 101)

    assert len(user_activity.get_watchlist(1)) == 1
    assert user_activity.get_watchlist(2) == []


def test_remove_from_watchlist(test_database):
    user_activity.add_to_watchlist(1, 101)

    assert user_activity.remove_from_watchlist(1, 101) is True
    assert user_activity.remove_from_watchlist(1, 101) is False

    assert user_activity.get_watchlist(1) == []


# ---------------- WATCH HISTORY TESTS ----------------

def test_add_to_watch_history(test_database):
    history_id = user_activity.add_to_watch_history(1, 101)

    assert isinstance(history_id, int)
    assert history_id > 0


def test_get_watch_history_returns_movie_details(test_database):
    user_activity.add_to_watch_history(1, 101)

    history = user_activity.get_watch_history(1)

    assert len(history) == 1
    assert history[0]["movie_id"] == 101
    assert history[0]["title"] == "Test Movie One"
    assert history[0]["release_year"] == 2020


def test_same_movie_can_be_recorded_multiple_times(test_database):
    first_id = user_activity.add_to_watch_history(1, 101)
    second_id = user_activity.add_to_watch_history(1, 101)

    assert first_id != second_id
    assert len(user_activity.get_watch_history(1)) == 2


def test_remove_specific_watch_history_entry(test_database):
    first_id = user_activity.add_to_watch_history(1, 101)
    second_id = user_activity.add_to_watch_history(1, 101)

    assert user_activity.remove_from_watch_history(1, second_id) is True

    history = user_activity.get_watch_history(1)

    assert len(history) == 1
    assert history[0]["watch_history_id"] == first_id


def test_user_cannot_remove_another_users_history(test_database):
    history_id = user_activity.add_to_watch_history(1, 101)

    assert user_activity.remove_from_watch_history(2, history_id) is False
    assert len(user_activity.get_watch_history(1)) == 1


# ---------------- RATING TESTS ----------------

def test_save_movie_rating(test_database):
    assert user_activity.save_movie_rating(1, 101, 4.5) is True

    feedback = user_activity.get_movie_feedback(1, 101)

    assert len(feedback) == 1
    assert feedback[0]["rating"] == 4.5
    assert feedback[0]["feedback_type"] == "rating"


def test_update_movie_rating_without_duplicate(test_database):
    user_activity.save_movie_rating(1, 101, 4.5)
    user_activity.save_movie_rating(1, 101, 3.5)

    feedback = user_activity.get_movie_feedback(1, 101)

    assert len(feedback) == 1
    assert feedback[0]["rating"] == 3.5


@pytest.mark.parametrize(
    "invalid_rating",
    [0, 5.5, 6, -1, 2.3, True, "4"]
)
def test_invalid_ratings_are_rejected(test_database, invalid_rating):
    with pytest.raises(ValueError):
        user_activity.save_movie_rating(1, 101, invalid_rating)


# ---------------- REACTION TESTS ----------------

def test_save_like_reaction(test_database):
    assert user_activity.save_movie_reaction(1, 101, True) is True

    feedback = user_activity.get_movie_feedback(1, 101)

    assert feedback[0]["liked"] == 1
    assert feedback[0]["feedback_type"] == "like"


def test_save_dislike_reaction(test_database):
    assert user_activity.save_movie_reaction(1, 101, False) is True

    feedback = user_activity.get_movie_feedback(1, 101)

    assert feedback[0]["liked"] == 0
    assert feedback[0]["feedback_type"] == "dislike"


def test_reaction_preserves_existing_rating(test_database):
    user_activity.save_movie_rating(1, 101, 3.5)
    user_activity.save_movie_reaction(1, 101, True)

    feedback = user_activity.get_movie_feedback(1, 101)

    assert feedback[0]["rating"] == 3.5
    assert feedback[0]["liked"] == 1


def test_invalid_reaction_is_rejected(test_database):
    with pytest.raises(ValueError):
        user_activity.save_movie_reaction(1, 101, 1)


# ---------------- FEEDBACK RETRIEVAL AND DELETION ----------------

def test_get_all_movie_feedback(test_database):
    user_activity.save_movie_rating(1, 101, 4.0)
    user_activity.save_movie_rating(1, 102, 3.5)

    feedback = user_activity.get_movie_feedback(1)

    assert len(feedback) == 2


def test_feedback_is_user_specific(test_database):
    user_activity.save_movie_rating(1, 101, 4.0)

    assert len(user_activity.get_movie_feedback(1)) == 1
    assert user_activity.get_movie_feedback(2) == []


def test_remove_movie_feedback(test_database):
    user_activity.save_movie_rating(1, 101, 4.0)

    assert user_activity.remove_movie_feedback(1, 101) is True
    assert user_activity.remove_movie_feedback(1, 101) is False

    assert user_activity.get_movie_feedback(1, 101) == []


def test_user_cannot_remove_another_users_feedback(test_database):
    user_activity.save_movie_rating(1, 101, 4.0)

    assert user_activity.remove_movie_feedback(2, 101) is False
    assert len(user_activity.get_movie_feedback(1, 101)) == 1
