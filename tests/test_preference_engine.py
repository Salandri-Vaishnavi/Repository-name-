import pytest

from src.recommendation.preference_engine import (
    PersonalizedRecommender
)


@pytest.fixture(scope="module")
def recommender():
    engine = PersonalizedRecommender()
    engine.load_and_train()
    return engine


def test_recommendations_are_generated(recommender):
    results = recommender.recommend(
        favorite_genres=["Action", "Sci-Fi"],
        favorite_movies=["Matrix, The (1999)"],
        top_n=5
    )

    assert not results.empty
    assert len(results) <= 5
    assert "similarity_score" in results.columns
    assert "ranking_score" in results.columns


def test_favorite_movie_is_excluded(recommender):
    results = recommender.recommend(
        favorite_genres=["Action"],
        favorite_movies=["Matrix, The (1999)"],
        top_n=10
    )

    assert "Matrix, The (1999)" not in results["title"].values


def test_disliked_movie_is_excluded(recommender):
    results = recommender.recommend(
        favorite_genres=["Action", "Sci-Fi"],
        disliked_movies=["Predators (2010)"],
        top_n=10
    )

    assert "Predators (2010)" not in results["title"].values


def test_invalid_genre_is_rejected(recommender):
    with pytest.raises(ValueError, match="Unsupported genre"):
        recommender.recommend(
            favorite_genres=["InvalidGenre"]
        )


def test_empty_preferences_are_rejected(recommender):
    with pytest.raises(ValueError, match="Select at least one"):
        recommender.recommend()


@pytest.mark.parametrize("invalid_count", [0, -1, 1.5, True])
def test_invalid_recommendation_count_is_rejected(
    recommender,
    invalid_count
):
    with pytest.raises(ValueError, match="top_n"):
        recommender.recommend(
            favorite_genres=["Action"],
            top_n=invalid_count
        )