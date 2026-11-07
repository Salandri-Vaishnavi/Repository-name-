
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


BASE_DIR = Path(__file__).resolve().parents[2]

DATA_FILE = BASE_DIR / "data" / "processed" / "processed_movies.csv"


class ContentBasedRecommender:

    def __init__(self):
        self.movies = None
        self.vectorizer = None
        self.tfidf_matrix = None

    def load_data(self):

        if not DATA_FILE.exists():
            raise FileNotFoundError(
                f"Dataset not found: {DATA_FILE}"
            )

        self.movies = pd.read_csv(DATA_FILE)

        self.movies["content"] = (
            self.movies["content"].fillna("").astype(str)
        )

        print(f"Loaded {len(self.movies)} movies.")

    def train(self):

        if self.movies is None:
            self.load_data()

        self.vectorizer = TfidfVectorizer(
            stop_words="english",
            ngram_range=(1, 2),
            min_df=1,
            max_features=20000
        )

        self.tfidf_matrix = self.vectorizer.fit_transform(
            self.movies["content"]
        )

        print("TF-IDF vectorization completed.")
        print("TF-IDF matrix shape:", self.tfidf_matrix.shape)






    def recommend(self, movie_title, top_n=10):

        if self.tfidf_matrix is None:
            self.train()

        if not isinstance(top_n, int) or top_n < 1:
            raise ValueError("top_n must be a positive integer.")

        if not movie_title or not movie_title.strip():
            raise ValueError("Please provide a movie title.")

        matches = self.movies[
            self.movies["title"].str.casefold()
            == movie_title.strip().casefold()
        ]

        if matches.empty:
            raise ValueError(f"Movie not found: {movie_title}")

        movie_index = matches.index[0]
        selected_movie = self.movies.iloc[movie_index]

        # Calculate content similarity
        similarity_scores = cosine_similarity(
            self.tfidf_matrix[movie_index],
            self.tfidf_matrix
        ).flatten()

        # Calculate normalized popularity
        rating_counts = self.movies["rating_count"].fillna(0).clip(lower=0)

        max_count = max(float(rating_counts.max()), 1.0)

        popularity_scores = (
            np.log1p(rating_counts) / np.log1p(max_count)
        )

        # Normalize average ratings
        average_ratings = (
            self.movies["average_rating"]
            .fillna(0)
            .clip(0, 5)
        )

        rating_scores = average_ratings / 5

        # Hybrid ranking
        ranking_scores = (
            0.75 * similarity_scores
            + 0.15 * rating_scores
            + 0.10 * popularity_scores
        )

        results = []

        selected_genres = set(
            str(selected_movie["genres"]).split("|")
        ) - {"(no genres listed)", ""}

        for index in range(len(self.movies)):

            # Exclude the selected movie itself
            if index == movie_index:
                continue

            recommended_movie = self.movies.iloc[index]

            recommended_genres = set(
                str(recommended_movie["genres"]).split("|")
            ) - {"(no genres listed)", ""}

            common_genres = sorted(
                selected_genres.intersection(recommended_genres)
            )

            if common_genres:
                explanation = (
                    "Shares genres: " + ", ".join(common_genres)
                )
            elif similarity_scores[index] > 0:
                explanation = "Similar movie content and tags"
            else:
                explanation = (
                    "Popular or highly rated fallback recommendation"
                )

            results.append({
                "movieId": recommended_movie["movieId"],
                "title": recommended_movie["title"],
                "year": recommended_movie["year"],
                "genres": recommended_movie["genres"],
                "average_rating": round(
                    float(average_ratings.iloc[index]), 2
                ),
                "rating_count": int(
                    rating_counts.iloc[index]
                ),
                "similarity_score": round(
                    float(similarity_scores[index]) * 100, 2
                ),
                "ranking_score": round(
                    float(ranking_scores.iloc[index]) * 100, 2
                ),
                "explanation": explanation
            })

        recommendations = pd.DataFrame(results)

        # Sort by hybrid ranking score
        recommendations = recommendations.sort_values(
            by=["ranking_score", "similarity_score"],
            ascending=False
        )

        # Return the requested number of recommendations
        return recommendations.head(top_n).reset_index(drop=True)






def main():

    print("\n========== CINEMATCH AI ==========")

    recommender = ContentBasedRecommender()

    recommender.load_data()
    recommender.train()

    selected_movie = "Matrix, The (1999)"

    
    print(f"\nSelected Movie: {selected_movie}")

    results = recommender.recommend(
        movie_title=selected_movie,
        top_n=10
    )

    print("\n========== HYBRID RECOMMENDATIONS ==========")

    if results.empty:
        print("No similar movies found.")
    else:
        print(




results[
    [
        "title",
        "year",
        "genres",
        "average_rating",
        "rating_count",
        "similarity_score",
        "ranking_score",
        "explanation"
    ]
]
            
            
            
            
            .to_string(index=False)
        )

    print("\nHybrid recommendation engine executed successfully!")


if __name__ == "__main__":
    main()
