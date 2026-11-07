
import pytest
import requests

from src.services import tmdb_service


class MockResponse:
    """Simulate a TMDB HTTP response."""

    def __init__(self, data, status_code=200):
        self.data = data
        self.status_code = status_code

    def json(self):
        return self.data

    def raise_for_status(self):
        if self.status_code >= 400:
            error = requests.exceptions.HTTPError(
                f"HTTP {self.status_code}"
            )
            error.response = self
            raise error


@pytest.fixture
def mock_tmdb_request(monkeypatch):
    """Mock requests.get without making real API calls."""

    responses = []

    def fake_get(url, headers=None, params=None, timeout=None):
        responses.append({
            "url": url,
            "headers": headers,
            "params": params,
            "timeout": timeout
        })

        return MockResponse({"results": []})

    monkeypatch.setenv(
        "TMDB_READ_ACCESS_TOKEN",
        "test-token"
    )

    monkeypatch.setattr(
        tmdb_service.requests,
        "get",
        fake_get
    )

    return responses


def test_empty_movie_search_returns_empty_list():
    assert tmdb_service.search_movies("") == []
    assert tmdb_service.search_movies("   ") == []


def test_movie_search_returns_results(mock_tmdb_request):
    def fake_get(url, headers=None, params=None, timeout=None):
        return MockResponse({
            "results": [
                {
                    "id": 176590,
                    "title": "Mirchi",
                    "original_language": "te"
                }
            ]
        })

    monkeypatch_response = fake_get

    tmdb_service.requests.get = monkeypatch_response

    results = tmdb_service.search_movies("Mirchi")

    assert len(results) == 1
    assert results[0]["title"] == "Mirchi"
    assert results[0]["id"] == 176590


def test_movie_search_uses_indian_region(mock_tmdb_request):
    tmdb_service.search_movies(
        "Mirchi",
        region="IN"
    )

    assert mock_tmdb_request[0]["url"].endswith(
        "/search/movie"
    )

    assert mock_tmdb_request[0]["params"]["region"] == "IN"


def test_invalid_search_page_is_rejected():
    for invalid_page in [0, -1, 1.5, True]:
        with pytest.raises(ValueError):
            tmdb_service.search_movies(
                "Mirchi",
                page=invalid_page
            )


def test_movie_details_include_required_sections(
    mock_tmdb_request
):
    tmdb_service.get_movie_details(176590)

    params = mock_tmdb_request[0]["params"]

    assert params["append_to_response"] == (
        "credits,videos,images"
    )


def test_person_search_returns_results(
    monkeypatch
):
    monkeypatch.setenv(
        "TMDB_READ_ACCESS_TOKEN",
        "test-token"
    )

    monkeypatch.setattr(
        tmdb_service.requests,
        "get",
        lambda *args, **kwargs: MockResponse({
            "results": [
                {
                    "id": 237,
                    "name": "Prabhas"
                }
            ]
        })
    )

    results = tmdb_service.search_people("Prabhas")

    assert results[0]["name"] == "Prabhas"


def test_watch_providers_return_indian_availability(
    monkeypatch
):
    monkeypatch.setenv(
        "TMDB_READ_ACCESS_TOKEN",
        "test-token"
    )

    monkeypatch.setattr(
        tmdb_service.requests,
        "get",
        lambda *args, **kwargs: MockResponse({
            "results": {
                "IN": {
                    "flatrate": [
                        {
                            "provider_name": "Amazon Prime Video"
                        }
                    ]
                }
            }
        })
    )

    result = tmdb_service.get_movie_watch_providers(
        176590,
        region="IN"
    )

    assert result["region"] == "IN"
    assert result["availability"]["flatrate"][0][
        "provider_name"
    ] == "Amazon Prime Video"

    assert "JustWatch" in result["attribution"]


def test_missing_provider_information_returns_none(
    monkeypatch
):
    monkeypatch.setenv(
        "TMDB_READ_ACCESS_TOKEN",
        "test-token"
    )

    monkeypatch.setattr(
        tmdb_service.requests,
        "get",
        lambda *args, **kwargs: MockResponse({
            "results": {}
        })
    )

    result = tmdb_service.get_movie_watch_providers(176590)

    assert result["availability"] is None


def test_missing_image_path_returns_none():
    assert tmdb_service.get_image_url(None) is None
    assert tmdb_service.get_image_url("") is None


def test_missing_token_raises_error(monkeypatch):
    monkeypatch.delenv(
        "TMDB_READ_ACCESS_TOKEN",
        raising=False
    )

    with pytest.raises(
        tmdb_service.TMDBAPIError,
        match="access token is missing"
    ):
        tmdb_service.get_tmdb_token()


def test_http_error_is_handled(
    monkeypatch
):
    monkeypatch.setenv(
        "TMDB_READ_ACCESS_TOKEN",
        "test-token"
    )

    monkeypatch.setattr(
        tmdb_service.requests,
        "get",
        lambda *args, **kwargs: MockResponse(
            {},
            status_code=401
        )
    )

    with pytest.raises(
        tmdb_service.TMDBAPIError
    ) as error:
        tmdb_service.search_movies("Mirchi")

    assert error.value.status_code == 401


def test_timeout_is_handled(
    monkeypatch
):
    monkeypatch.setenv(
        "TMDB_READ_ACCESS_TOKEN",
        "test-token"
    )

    def raise_timeout(*args, **kwargs):
        raise requests.exceptions.Timeout()

    monkeypatch.setattr(
        tmdb_service.requests,
        "get",
        raise_timeout
    )

    with pytest.raises(
        tmdb_service.TMDBAPIError,
        match="timed out"
    ):
        tmdb_service.search_movies("Mirchi")
