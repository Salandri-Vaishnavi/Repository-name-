
from src.database.connection import get_connection


def create_tables():
    """
    Create all CineMatch AI database tables.
    """

    with get_connection() as connection:

        cursor = connection.cursor()

        # 1. Users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL COLLATE NOCASE UNIQUE,
                email TEXT NOT NULL COLLATE NOCASE UNIQUE,
                password_hash TEXT NOT NULL,
                full_name TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                is_active INTEGER NOT NULL DEFAULT 1
                    CHECK (is_active IN (0, 1))
            )
        """)

        # 2. Movies table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS movies (
                movie_id INTEGER PRIMARY KEY,
                title TEXT NOT NULL,
                clean_title TEXT,
                release_year INTEGER,
                genres TEXT NOT NULL DEFAULT '',
                overview TEXT,
                poster_url TEXT,
                backdrop_url TEXT,
                average_rating REAL NOT NULL DEFAULT 0
                    CHECK (average_rating BETWEEN 0 AND 5),
                rating_count INTEGER NOT NULL DEFAULT 0
                    CHECK (rating_count >= 0),
                bayesian_rating REAL NOT NULL DEFAULT 0
                    CHECK (bayesian_rating BETWEEN 0 AND 5),
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 3. User preferences table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_preferences (
                preference_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL UNIQUE,
                preferred_language TEXT DEFAULT 'English',
                preferred_release_period TEXT,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (user_id)
                    REFERENCES users(user_id)
                    ON DELETE CASCADE
            )
        """)

        # 4. User favorite genres table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_genres (
                user_genre_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                genre TEXT NOT NULL COLLATE NOCASE,

                UNIQUE (user_id, genre),

                FOREIGN KEY (user_id)
                    REFERENCES users(user_id)
                    ON DELETE CASCADE
            )
        """)

        # 5. User movie feedback table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_movie_feedback (
                feedback_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                movie_id INTEGER NOT NULL,
                rating REAL
                    CHECK (rating IS NULL OR rating BETWEEN 0.5 AND 5),
                liked INTEGER
                    CHECK (liked IS NULL OR liked IN (0, 1)),
                feedback_type TEXT NOT NULL DEFAULT 'rating'
                    CHECK (
                        feedback_type IN (
                            'rating',
                            'like',
                            'dislike',
                            'watched'
                        )
                    ),
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

                UNIQUE (user_id, movie_id),

                FOREIGN KEY (user_id)
                    REFERENCES users(user_id)
                    ON DELETE CASCADE,

                FOREIGN KEY (movie_id)
                    REFERENCES movies(movie_id)
                    ON DELETE CASCADE
            )
        """)

        # 6. Watchlist table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS watchlist (
                watchlist_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                movie_id INTEGER NOT NULL,
                added_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

                UNIQUE (user_id, movie_id),

                FOREIGN KEY (user_id)
                    REFERENCES users(user_id)
                    ON DELETE CASCADE,

                FOREIGN KEY (movie_id)
                    REFERENCES movies(movie_id)
                    ON DELETE CASCADE
            )
        """)

        # 7. Recommendation history table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS recommendation_history (
                history_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                recommendation_type TEXT NOT NULL,
                input_movie_id INTEGER,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (user_id)
                    REFERENCES users(user_id)
                    ON DELETE CASCADE,

                FOREIGN KEY (input_movie_id)
                    REFERENCES movies(movie_id)
                    ON DELETE SET NULL
            )
        """)

        # 8. Recommendation items table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS recommendation_items (
                item_id INTEGER PRIMARY KEY AUTOINCREMENT,
                history_id INTEGER NOT NULL,
                movie_id INTEGER NOT NULL,
                similarity_score REAL,
                ranking_score REAL,
                recommendation_position INTEGER NOT NULL
                    CHECK (recommendation_position > 0),
                explanation TEXT,

                UNIQUE (history_id, movie_id),
                UNIQUE (history_id, recommendation_position),

                FOREIGN KEY (history_id)
                    REFERENCES recommendation_history(history_id)
                    ON DELETE CASCADE,

                FOREIGN KEY (movie_id)
                    REFERENCES movies(movie_id)
                    ON DELETE CASCADE
            )
        """)
        # 9. User watch history table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS watch_history (
                watch_history_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                movie_id INTEGER NOT NULL,
                watched_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (user_id)
                    REFERENCES users(user_id)
                    ON DELETE CASCADE,

                FOREIGN KEY (movie_id)
                    REFERENCES movies(movie_id)
                    ON DELETE CASCADE
            )
        """)

        # Index for faster user watch history retrieval
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_watch_history_user
            ON watch_history(user_id)
        """)





        # Create indexes for frequently queried columns
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_movies_title
            ON movies(title)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_movies_rating
            ON movies(average_rating)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_feedback_user
            ON user_movie_feedback(user_id)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_watchlist_user
            ON watchlist(user_id)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_history_user
            ON recommendation_history(user_id)
        """)

        print("CineMatch AI database tables created successfully!")


if __name__ == "__main__":
    create_tables()
