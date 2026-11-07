
import sqlite3
from contextlib import contextmanager
from pathlib import Path


# Project directory
BASE_DIR = Path(__file__).resolve().parents[2]

# Database directory and file
DATABASE_DIR = BASE_DIR / "data"
DATABASE_FILE = DATABASE_DIR / "cinematch.db"


@contextmanager
def get_connection():
    """
    Create and manage a SQLite database connection.

    Automatically commits successful transactions,
    rolls back failed transactions and closes connections.
    """

    DATABASE_DIR.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(
        DATABASE_FILE,
        timeout=10
    )

    connection.row_factory = sqlite3.Row

    try:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 10000")

        yield connection

        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()
