
from pathlib import Path

import numpy as np
import pandas as pd

from src.database.connection import get_connection


BASE_DIR = Path(__file__).resolve().parents[2]

PROCESSED_FILE = (
    BASE_DIR
    / "data"
    / "processed"
    / "processed_movies.csv"
)

MINIMUM_RATING_COUNT = 20


def load_processed_movies():
    """Load and validate the processed MovieLens dataset."""

    if not PROCESSED_FILE.exists():
        raise FileNotFoundError(
            f"Processed movie dataset not found: {PROCESSED_FILE}"
        )

    movies = pd.read_csv(PROCESSED_FILE)

    required_columns = {
        "movieId",
        "title",
        "clean_title",
        "year",
        "genres",
        "average_rating",
        "rating_count"
    }

    missing_columns = required_columns - set(movies.columns)

    if missing_columns:
        raise ValueError(
            f"Missing required columns: {sorted(missing_columns)}"
        )

    if movies["movieId"].isna().any():
        raise ValueError("Movie IDs cannot be empty.")

    if movies["title"].isna().any():
        raise ValueError("Movie titles cannot be empty.")

    if movies["movieId"].duplicated().any():
        raise ValueError("Duplicate movie IDs found.")

    return movies


def calculate_bayesian_ratings(movies):
    """Calculate confidence-adjusted movie ratings."""

    ratings = movies["average_rating"].fillna(0).to_numpy(
        dtype=float
    )

    counts = movies["rating_count"].fillna(0).to_numpy(
        dtype=float
    )

    total_ratings = counts.sum()

    if total_ratings > 0:
        global_average = np.average(
            ratings,
            weights=counts
        )
    else:
        global_average = 0.0

    minimum_count = MINIMUM_RATING_COUNT

    bayesian_ratings = (
        counts / (counts + minimum_count) * ratings
        +
        minimum_count / (counts + minimum_count)
        * global_average
    )

    return bayesian_ratings


def prepare_movie_records(movies):
    """Prepare records for SQLite insertion."""

    bayesian_ratings = calculate_bayesian_ratings(movies)

    records = []

    for position, (_, movie) in enumerate(movies.iterrows()):

        year = movie["year"]

        if pd.isna(year):
            year = None
        else:
            year = int(year)

        records.append((
            int(movie["movieId"]),
            str(movie["title"]),
            (
                str(movie["clean_title"])
                if pd.notna(movie["clean_title"])
                else None
            ),
            year,
            (
                str(movie["genres"])
                if pd.notna(movie["genres"])
                else ""
            ),
            float(movie["average_rating"])
            if pd.notna(movie["average_rating"])
            else 0.0,
            int(movie["rating_count"])
            if pd.notna(movie["rating_count"])
            else 0,
            float(bayesian_ratings[position])
        ))

    return records


def seed_movies():
    """Import processed movies into the CineMatch database."""

    print("\n========== CINEMATCH AI MOVIE IMPORT ==========")

    print("\nLoading processed movie dataset...")

    movies = load_processed_movies()

    print("Movies loaded:", len(movies))

    print("\nCalculating Bayesian-adjusted ratings...")

    records = prepare_movie_records(movies)

    print("\nImporting movies into SQLite...")

    with get_connection() as connection:

        connection.executemany(
            """
            INSERT INTO movies (
                movie_id,
                title,
                clean_title,
                release_year,
                genres,
                average_rating,
                rating_count,
                bayesian_rating
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)

            ON CONFLICT(movie_id)
            DO UPDATE SET
                title = excluded.title,
                clean_title = excluded.clean_title,
                release_year = excluded.release_year,
                genres = excluded.genres,
                average_rating = excluded.average_rating,
                rating_count = excluded.rating_count,
                bayesian_rating = excluded.bayesian_rating
            """,
            records
        )

        total_movies = connection.execute(
            "SELECT COUNT(*) FROM movies"
        ).fetchone()[0]

        sample = connection.execute(
            """
            SELECT title, release_year, genres,
                   average_rating, rating_count,
                   bayesian_rating
            FROM movies
            WHERE title = ?
            """,
            ("Toy Story (1995)",)
        ).fetchone()

    print("\n========== IMPORT RESULTS ==========")

    print("Movies in database:", total_movies)

    if sample:
        print("\nSample imported movie:")
        print("Title:", sample["title"])
        print("Year:", sample["release_year"])
        print("Genres:", sample["genres"])
        print("Average rating:", sample["average_rating"])
        print("Rating count:", sample["rating_count"])
        print("Bayesian rating:", round(sample["bayesian_rating"], 2))

    print("\nMovie catalog import completed successfully!")


if __name__ == "__main__":
    seed_movies()
48
