
import re
from pathlib import Path

import pandas as pd


# Project paths
BASE_DIR = Path(__file__).resolve().parents[2]

RAW_DATA_DIR = BASE_DIR / "data" / "raw" / "ml-latest-small"
PROCESSED_DATA_DIR = BASE_DIR / "data" / "processed"

MOVIES_FILE = RAW_DATA_DIR / "movies.csv"
RATINGS_FILE = RAW_DATA_DIR / "ratings.csv"
TAGS_FILE = RAW_DATA_DIR / "tags.csv"

OUTPUT_FILE = PROCESSED_DATA_DIR / "processed_movies.csv"


def extract_year(title):
    """Extract the release year from a movie title."""

    match = re.search(r"\((\d{4})\)\s*$", str(title))

    if match:
        return int(match.group(1))

    return None


def load_datasets():
    """Load the original MovieLens CSV files."""

    movies = pd.read_csv(MOVIES_FILE)
    ratings = pd.read_csv(RATINGS_FILE)
    tags = pd.read_csv(TAGS_FILE)

    return movies, ratings, tags


def preprocess_movies(movies, ratings, tags):
    """Combine movie metadata, tags and rating statistics."""

    movies = movies.copy()

    # Extract movie release year
    movies["year"] = movies["title"].apply(extract_year)

    # Separate movie title from release year
    movies["clean_title"] = movies["title"].str.replace(
        r"\s*\(\d{4}\)\s*$",
        "",
        regex=True
    )

    # Convert genres into readable text
    movies["genres_text"] = (
        movies["genres"]
        .str.replace("|", " ", regex=False)
        .str.replace("(no genres listed)", "", regex=False)
    )

    # Combine all tags belonging to each movie
    tag_data = (
        tags.dropna(subset=["tag"])
        .assign(tag=lambda df: df["tag"].astype(str).str.lower().str.strip())
        .groupby("movieId")["tag"]
        .apply(lambda values: " ".join(sorted(set(values))))
        .reset_index(name="tags_text")
    )

    # Calculate average rating and number of ratings
    rating_data = (
        ratings.groupby("movieId")
        .agg(
            average_rating=("rating", "mean"),
            rating_count=("rating", "count")
        )
        .reset_index()
    )

    # Merge additional information
    processed = movies.merge(
        tag_data,
        on="movieId",
        how="left"
    )

    processed = processed.merge(
        rating_data,
        on="movieId",
        how="left"
    )

    # Fill missing values
    processed["tags_text"] = processed["tags_text"].fillna("")
    processed["average_rating"] = processed["average_rating"].fillna(0)
    processed["rating_count"] = processed["rating_count"].fillna(0)

    # Create the content used by the recommendation engine
    processed["content"] = (
        processed["genres_text"].fillna("")
        + " "
        + processed["tags_text"].fillna("")
    ).str.strip()

    # Remove duplicate movies if any
    processed = processed.drop_duplicates(subset=["movieId"])

    # Keep a clean and useful column order
    processed = processed[
        [
            "movieId",
            "title",
            "clean_title",
            "year",
            "genres",
            "genres_text",
            "tags_text",
            "average_rating",
            "rating_count",
            "content"
        ]
    ]

    return processed


def main():
    """Execute the complete preprocessing workflow."""

    print("\n========== CINEMATCH AI PREPROCESSING ==========")

    PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)

    print("\nLoading MovieLens datasets...")

    movies, ratings, tags = load_datasets()

    print("Movies loaded:", len(movies))
    print("Ratings loaded:", len(ratings))
    print("Tags loaded:", len(tags))

    print("\nPreprocessing movie information...")

    processed_movies = preprocess_movies(
        movies,
        ratings,
        tags
    )

    print("\nSaving processed movie dataset...")

    processed_movies.to_csv(
        OUTPUT_FILE,
        index=False,
        encoding="utf-8"
    )

    print("\n========== PREPROCESSING RESULTS ==========")

    print("Total processed movies:", len(processed_movies))
    print("Movies with tags:", (processed_movies["tags_text"] != "").sum())
    print("Movies without tags:", (processed_movies["tags_text"] == "").sum())

    print("\nSample processed movies:")

    print(
        processed_movies[
            ["title", "genres", "average_rating", "rating_count", "content"]
        ].head(5).to_string(index=False)
    )

    print("\nSaved file:", OUTPUT_FILE)

    print("\nCineMatch AI preprocessing completed successfully!")


if __name__ == "__main__":
    main()
