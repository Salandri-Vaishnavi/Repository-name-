from src.database.connection import get_connection


def add_to_watchlist(user_id, movie_id):
    """Add a movie to the logged-in user's watchlist."""

    if not isinstance(user_id, int) or user_id <= 0:
        raise ValueError("A valid user ID is required.")

    if not isinstance(movie_id, int) or movie_id <= 0:
        raise ValueError("A valid movie ID is required.")

    with get_connection() as connection:
        cursor = connection.cursor()

        cursor.execute(
            """
            INSERT OR IGNORE INTO watchlist (user_id, movie_id)
            VALUES (?, ?)
            """,
            (user_id, movie_id)
        )

        return cursor.rowcount == 1


def add_tmdb_movie_to_watchlist(user_id, movie):
    """Save a TMDB movie and add it to the user's watchlist."""

    if not isinstance(user_id, int) or user_id <= 0:
        raise ValueError("A valid user ID is required.")

    if not isinstance(movie, dict):
        raise ValueError("A valid movie dictionary is required.")

    tmdb_id = movie.get("id")

    if not isinstance(tmdb_id, int) or tmdb_id <= 0:
        raise ValueError("A valid TMDB movie ID is required.")

    # Keep TMDB-only IDs separate from MovieLens IDs.
    movie_id = 1_000_000_000 + tmdb_id

    title = str(movie.get("title") or "").strip()

    if not title:
        raise ValueError("A movie title is required.")

    release_date = movie.get("release_date") or ""
    release_year = None

    if len(release_date) >= 4 and release_date[:4].isdigit():
        release_year = int(release_date[:4])

    genres = movie.get("genres", "")
    if isinstance(genres, list):
        genres = "|".join(str(genre) for genre in genres)

    vote_average = float(movie.get("vote_average") or 0)
    average_rating = max(0, min(5, vote_average / 2))

    rating_count = int(movie.get("vote_count") or 0)

    poster_url = movie.get("poster_url")
    backdrop_url = movie.get("backdrop_url")

    with get_connection() as connection:
        cursor = connection.cursor()

        cursor.execute(
            """
            INSERT OR IGNORE INTO movies (
                movie_id,
                title,
                release_year,
                genres,
                overview,
                poster_url,
                backdrop_url,
                average_rating,
                rating_count,
                bayesian_rating
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                movie_id,
                title,
                release_year,
                str(genres or ""),
                movie.get("overview") or "",
                poster_url,
                backdrop_url,
                average_rating,
                rating_count,
                average_rating,
            ),
        )

        cursor.execute(
            """
            INSERT OR IGNORE INTO watchlist (user_id, movie_id)
            VALUES (?, ?)
            """,
            (user_id, movie_id),
        )

        return cursor.rowcount == 1




def remove_from_watchlist(user_id, movie_id):
    """Remove a movie from the logged-in user's watchlist."""

    if not isinstance(user_id, int) or user_id <= 0:
        raise ValueError("A valid user ID is required.")

    if not isinstance(movie_id, int) or movie_id <= 0:
        raise ValueError("A valid movie ID is required.")

    with get_connection() as connection:
        cursor = connection.cursor()

        cursor.execute(
            """
            DELETE FROM watchlist
            WHERE user_id = ? AND movie_id = ?
            """,
            (user_id, movie_id)
        )

        return cursor.rowcount == 1


def get_watchlist(user_id):
    """Retrieve the logged-in user's watchlist."""

    if not isinstance(user_id, int) or user_id <= 0:
        raise ValueError("A valid user ID is required.")

    with get_connection() as connection:
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT
                m.movie_id,
                m.title,
                m.release_year,
                m.genres,

                m.average_rating,
                m.rating_count,
                m.poster_url,
                m.backdrop_url,
                m.overview,
                w.added_at



            FROM watchlist AS w
            INNER JOIN movies AS m
                ON w.movie_id = m.movie_id
            WHERE w.user_id = ?
            ORDER BY w.added_at DESC
            """,
            (user_id,)
        )

        return [dict(row) for row in cursor.fetchall()]


def add_to_watch_history(user_id, movie_id):
    """Record a movie viewing event for a user."""

    if not isinstance(user_id, int) or user_id <= 0:
        raise ValueError("A valid user ID is required.")

    if not isinstance(movie_id, int) or movie_id <= 0:
        raise ValueError("A valid movie ID is required.")

    with get_connection() as connection:
        cursor = connection.cursor()

        cursor.execute(
            """
            INSERT INTO watch_history (user_id, movie_id)
            VALUES (?, ?)
            """,
            (user_id, movie_id)
        )

        return cursor.lastrowid


def get_watch_history(user_id):
    """Retrieve a user's watch history with movie details."""

    if not isinstance(user_id, int) or user_id <= 0:
        raise ValueError("A valid user ID is required.")

    with get_connection() as connection:
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT
                wh.watch_history_id,
                wh.movie_id,
                m.title,
                m.release_year,
                m.genres,
                m.average_rating,
                m.poster_url,
                wh.watched_at
            FROM watch_history AS wh
            INNER JOIN movies AS m
                ON wh.movie_id = m.movie_id
            WHERE wh.user_id = ?
            ORDER BY wh.watched_at DESC, wh.watch_history_id DESC
            """,
            (user_id,)
        )

        return [dict(row) for row in cursor.fetchall()]


def remove_from_watch_history(user_id, watch_history_id):
    """Remove one specific viewing event from a user's history."""

    if not isinstance(user_id, int) or user_id <= 0:
        raise ValueError("A valid user ID is required.")

    if not isinstance(watch_history_id, int) or watch_history_id <= 0:
        raise ValueError("A valid watch history ID is required.")

    with get_connection() as connection:
        cursor = connection.cursor()

        cursor.execute(
            """
            DELETE FROM watch_history
            WHERE user_id = ? AND watch_history_id = ?
            """,
            (user_id, watch_history_id)
        )

        return cursor.rowcount == 1



def save_movie_rating(user_id, movie_id, rating):
    """Save or update a user's rating for a movie."""

    if not isinstance(user_id, int) or user_id <= 0:
        raise ValueError("A valid user ID is required.")

    if not isinstance(movie_id, int) or movie_id <= 0:
        raise ValueError("A valid movie ID is required.")

    if (
        isinstance(rating, bool)
        or not isinstance(rating, (int, float))
        or not 0.5 <= rating <= 5
        or rating * 2 != int(rating * 2)
    ):
        raise ValueError("Rating must be between 0.5 and 5 in 0.5 increments.")

    with get_connection() as connection:
        cursor = connection.cursor()

        cursor.execute(
            """
            INSERT INTO user_movie_feedback (
                user_id, movie_id, rating, feedback_type
            )
            VALUES (?, ?, ?, 'rating')
            ON CONFLICT(user_id, movie_id)
            DO UPDATE SET
                rating = excluded.rating,
                updated_at = CURRENT_TIMESTAMP
            """,
            (user_id, movie_id, float(rating))
        )

        return True


def save_movie_reaction(user_id, movie_id, liked):
    """Save or update a user's like or dislike reaction."""

    if not isinstance(user_id, int) or user_id <= 0:
        raise ValueError("A valid user ID is required.")

    if not isinstance(movie_id, int) or movie_id <= 0:
        raise ValueError("A valid movie ID is required.")

    if not isinstance(liked, bool):
        raise ValueError("Reaction must be True for like or False for dislike.")

    feedback_type = "like" if liked else "dislike"

    with get_connection() as connection:
        cursor = connection.cursor()

        cursor.execute(
            """
            INSERT INTO user_movie_feedback (
                user_id, movie_id, liked, feedback_type
            )
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id, movie_id)
            DO UPDATE SET
                liked = excluded.liked,
                feedback_type = excluded.feedback_type,
                updated_at = CURRENT_TIMESTAMP
            """,
            (user_id, movie_id, int(liked), feedback_type)
        )

        return True


def get_movie_feedback(user_id, movie_id=None):
    """Retrieve feedback submitted by a user."""

    if not isinstance(user_id, int) or user_id <= 0:
        raise ValueError("A valid user ID is required.")

    with get_connection() as connection:
        cursor = connection.cursor()

        if movie_id is not None:
            if not isinstance(movie_id, int) or movie_id <= 0:
                raise ValueError("A valid movie ID is required.")

            cursor.execute(
                """
                SELECT
                    f.feedback_id,
                    f.movie_id,
                    m.title,
                    f.rating,
                    f.liked,
                    f.feedback_type,
                    f.created_at,
                    f.updated_at
                FROM user_movie_feedback AS f
                INNER JOIN movies AS m
                    ON f.movie_id = m.movie_id
                WHERE f.user_id = ? AND f.movie_id = ?
                """,
                (user_id, movie_id)
            )
        else:
            cursor.execute(
                """
                SELECT
                    f.feedback_id,
                    f.movie_id,
                    m.title,
                    f.rating,
                    f.liked,
                    f.feedback_type,
                    f.created_at,
                    f.updated_at
                FROM user_movie_feedback AS f
                INNER JOIN movies AS m
                    ON f.movie_id = m.movie_id
                WHERE f.user_id = ?
                ORDER BY f.updated_at DESC
                """,
                (user_id,)
            )

        return [dict(row) for row in cursor.fetchall()]


def remove_movie_feedback(user_id, movie_id):
    """Remove a user's feedback for a specific movie."""

    if not isinstance(user_id, int) or user_id <= 0:
        raise ValueError("A valid user ID is required.")

    if not isinstance(movie_id, int) or movie_id <= 0:
        raise ValueError("A valid movie ID is required.")

    with get_connection() as connection:
        cursor = connection.cursor()

        cursor.execute(
            """
            DELETE FROM user_movie_feedback
            WHERE user_id = ? AND movie_id = ?
            """,
            (user_id, movie_id)
        )

        return cursor.rowcount == 1


