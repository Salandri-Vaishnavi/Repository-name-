
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity

from .tfidf_engine import ContentBasedRecommender


class PersonalizedRecommender:
    """
    Generates personalized movie recommendations using:
    1. Favorite genres
    2. Favorite movies
    3. Disliked movie exclusions
    4. TF-IDF content similarity
    5. Bayesian rating confidence
    6. Movie popularity
    """

    MINIMUM_RATING_COUNT = 20

    SIMILARITY_WEIGHT = 0.75
    RATING_WEIGHT = 0.20
    POPULARITY_WEIGHT = 0.05

    def __init__(self):
        self.engine = ContentBasedRecommender()
        self.movies = None
        self.trained = False

    def load_and_train(self):
        """Load the existing processed dataset and train TF-IDF."""

        self.engine.load_data()
        self.engine.train()

        self.movies = self.engine.movies
        self.trained = True

        print("Personalized recommendation engine is ready.")

    @staticmethod
    def _clean_input(values):
        """Validate and normalize a list of user preferences."""

        if values is None:
            return []

        if isinstance(values, str):
            values = [values]

        if not isinstance(values, (list, tuple, set)):
            raise ValueError(
                "Preferences must be provided as a list of strings."
            )

        cleaned = []

        for value in values:
            if not isinstance(value, str) or not value.strip():
                raise ValueError(
                    "Every preference must be a non-empty string."
                )

            value = value.strip()

            if value.casefold() not in {
                item.casefold() for item in cleaned
            }:
                cleaned.append(value)

        return cleaned

    def _get_movie_index(self, title):
        """Find a movie using its exact dataset title."""

        matches = self.movies[
            self.movies["title"].str.casefold()
            == title.casefold()
        ]

        if matches.empty:
            raise ValueError(
                f"Movie not found in dataset: {title}"
            )

        return int(matches.index[0])

    def _validate_genres(self, favorite_genres):
        """Validate selected genres against available movie genres."""

        available_genres = set()

        for genres in self.movies["genres"].fillna(""):
            available_genres.update(
                genre
                for genre in str(genres).split("|")
                if genre and genre != "(no genres listed)"
            )

        genre_lookup = {
            genre.casefold(): genre
            for genre in available_genres
        }

        validated = []

        for genre in favorite_genres:
            matched_genre = genre_lookup.get(genre.casefold())

            if matched_genre is None:
                raise ValueError(
                    f"Unsupported genre: {genre}. "
                    f"Available genres: {sorted(available_genres)}"
                )

            validated.append(matched_genre)

        return validated

    def _build_profile(
        self,
        favorite_genres,
        favorite_movies
    ):
        """Build a combined user preference vector."""

        profile_parts = []
        profile_weights = []

        # Genre preference vector
        if favorite_genres:

            genre_text = " ".join(favorite_genres)

            genre_vector = self.engine.vectorizer.transform(
                [genre_text]
            )

            if genre_vector.nnz > 0:
                profile_parts.append(genre_vector)
                profile_weights.append(0.5)

        # Favorite movie preference vector
        if favorite_movies:

            movie_indices = [
                self._get_movie_index(title)
                for title in favorite_movies
            ]

            movie_vectors = [
                self.engine.tfidf_matrix[index]
                for index in movie_indices
            ]

            movie_profile = movie_vectors[0].copy()

            for vector in movie_vectors[1:]:
                movie_profile += vector

            movie_profile = movie_profile / len(movie_vectors)

            if movie_profile.nnz > 0:
                profile_parts.append(movie_profile)
                profile_weights.append(0.5)

        if not profile_parts:
            raise ValueError(
                "Unable to build a preference profile. "
                "Please select valid genres or favorite movies "
                "with available content."
            )

        total_weight = sum(profile_weights)

        user_profile = profile_parts[0] * (
            profile_weights[0] / total_weight
        )

        for vector, weight in zip(
            profile_parts[1:],
            profile_weights[1:]
        ):
            user_profile += vector * (
                weight / total_weight
            )

        return user_profile

    def _calculate_bayesian_ratings(self):
        """
        Calculate confidence-adjusted ratings.

        Movies with fewer ratings are pulled closer
        to the global average rating.
        """

        ratings = self.movies["average_rating"].to_numpy(
            dtype=float
        )

        counts = self.movies["rating_count"].to_numpy(
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

        minimum_count = self.MINIMUM_RATING_COUNT

        bayesian_ratings = (
            (
                counts / (counts + minimum_count)
            ) * ratings
            +
            (
                minimum_count / (counts + minimum_count)
            ) * global_average
        )

        return bayesian_ratings, global_average

    def recommend(
        self,
        favorite_genres=None,
        favorite_movies=None,
        disliked_movies=None,
        top_n=10
    ):
        """Generate personalized movie recommendations."""

        if not self.trained:
            self.load_and_train()

        if (
            isinstance(top_n, bool)
            or not isinstance(top_n, int)
            or top_n < 1
        ):
            raise ValueError(
                "top_n must be a positive integer."
            )

        favorite_genres = self._clean_input(
            favorite_genres
        )

        favorite_movies = self._clean_input(
            favorite_movies
        )

        disliked_movies = self._clean_input(
            disliked_movies
        )

        favorite_genres = self._validate_genres(
            favorite_genres
        )

        if not favorite_genres and not favorite_movies:
            raise ValueError(
                "Select at least one favorite genre "
                "or favorite movie."
            )

        # Build user preference profile
        user_profile = self._build_profile(
            favorite_genres,
            favorite_movies
        )

        # Calculate content similarity
        similarity_scores = cosine_similarity(
            user_profile,
            self.engine.tfidf_matrix
        ).flatten()

        # Calculate confidence-adjusted movie ratings
        bayesian_ratings, global_average = (
            self._calculate_bayesian_ratings()
        )

        rating_scores = bayesian_ratings / 5.0

        # Calculate normalized popularity
        rating_counts = self.movies[
            "rating_count"
        ].to_numpy(dtype=float)

        max_count = max(
            float(rating_counts.max()),
            1.0
        )

        popularity_scores = (
            np.log1p(rating_counts)
            / np.log1p(max_count)
        )

        # Calculate personalized ranking
        ranking_scores = (
            self.SIMILARITY_WEIGHT * similarity_scores
            + self.RATING_WEIGHT * rating_scores
            + self.POPULARITY_WEIGHT * popularity_scores
        )

        # Exclude favorite and disliked movies
        excluded_indices = set()

        for title in favorite_movies + disliked_movies:
            excluded_indices.add(
                self._get_movie_index(title)
            )

        results = []

        favorite_genre_set = {
            genre.casefold()
            for genre in favorite_genres
        }

        for index in range(len(self.movies)):

            if index in excluded_indices:
                continue

            if similarity_scores[index] <= 0:
                continue

            movie = self.movies.iloc[index]

            movie_genres = {
                genre
                for genre in str(movie["genres"]).split("|")
                if genre and genre != "(no genres listed)"
            }

            matching_genres = sorted(
                genre
                for genre in movie_genres
                if genre.casefold() in favorite_genre_set
            )

            if matching_genres:
                explanation = (
                    "Matches your favorite genres: "
                    + ", ".join(matching_genres)
                )
            elif favorite_movies:
                explanation = (
                    "Similar content to your favorite movies"
                )
            else:
                explanation = (
                    "Matches your movie preference profile"
                )

            results.append({
                "movieId": int(movie["movieId"]),
                "title": movie["title"],
                "genres": movie["genres"],
                "year": movie["year"],
                "average_rating": round(
                    float(movie["average_rating"]), 2
                ),
                "rating_count": int(
                    movie["rating_count"]
                ),
                "bayesian_rating": round(
                    float(bayesian_ratings[index]), 2
                ),
                "similarity_score": round(
                    float(similarity_scores[index]) * 100, 2
                ),
                "ranking_score": round(
                    float(ranking_scores[index]) * 100, 2
                ),
                "explanation": explanation
            })

        recommendations = pd.DataFrame(results)

        if recommendations.empty:
            return recommendations

        recommendations = recommendations.sort_values(
            by=[
                "ranking_score",
                "similarity_score"
            ],
            ascending=False
        )

        return recommendations.head(
            top_n
        ).reset_index(drop=True)


def main():

    print("\n========== CINEMATCH AI ==========")
    print("PERSONALIZED RECOMMENDATION TEST")

    recommender = PersonalizedRecommender()

    results = recommender.recommend(
        favorite_genres=[
            "Action",
            "Sci-Fi",
            "Thriller"
        ],
        favorite_movies=[
            "Matrix, The (1999)"
        ],
        disliked_movies=[],
        top_n=10
    )

    print("\n========== USER PREFERENCES ==========")

    print("Favorite genres: Action, Sci-Fi, Thriller")
    print("Favorite movie: Matrix, The (1999)")

    print("\n========== PERSONALIZED RECOMMENDATIONS ==========")

    print(
        results[
            [
                "title",
                "genres",
                "average_rating",
                "rating_count",
                "bayesian_rating",
                "similarity_score",
                "ranking_score",
                "explanation"
            ]
        ].to_string(index=False)
    )

    print(
        "\nPersonalized recommendation engine "
        "executed successfully!"
    )


if __name__ == "__main__":
    main()
