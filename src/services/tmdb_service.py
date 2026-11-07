
import os
from functools import lru_cache
from pathlib import Path

import requests
from dotenv import load_dotenv


# --------------------------------------------------
# PROJECT CONFIGURATION
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parents[2]

ENV_FILE = BASE_DIR / ".env"

load_dotenv(dotenv_path=ENV_FILE)

TMDB_BASE_URL = "https://api.themoviedb.org/3"

DEFAULT_REGION = "IN"
DEFAULT_LANGUAGE = "en-US"
REQUEST_TIMEOUT = 20

# TMDB watch-provider data is powered by JustWatch.
WATCH_PROVIDER_ATTRIBUTION = (
    "Streaming availability data provided by JustWatch."
)


# --------------------------------------------------
# CUSTOM API EXCEPTION
# --------------------------------------------------

class TMDBAPIError(Exception):
    """Raised when a TMDB API request fails."""

    def __init__(self, message, status_code=None):
        super().__init__(message)
        self.status_code = status_code


# --------------------------------------------------
# AUTHENTICATION AND API REQUESTS
# --------------------------------------------------

def get_tmdb_token():
    """Retrieve the TMDB access token from the environment."""

    token = os.getenv("TMDB_READ_ACCESS_TOKEN")

    if not token:
        raise TMDBAPIError(
            "TMDB access token is missing. "
            "Check the project's .env file."
        )

    return token


def _make_request(endpoint, params=None):
    """Send an authenticated request to the TMDB API."""

    headers = {
        "Authorization": f"Bearer {get_tmdb_token()}",
        "accept": "application/json"
    }

    url = f"{TMDB_BASE_URL}/{endpoint.lstrip('/')}"

    try:
        response = requests.get(
            url,
            headers=headers,
            params=params,
            timeout=REQUEST_TIMEOUT
        )

        response.raise_for_status()

        return response.json()

    except requests.exceptions.HTTPError as error:
        status_code = (
            error.response.status_code
            if error.response is not None
            else None
        )

        raise TMDBAPIError(
            f"TMDB returned an HTTP error ({status_code}).",
            status_code=status_code
        ) from error

    except requests.exceptions.Timeout as error:
        raise TMDBAPIError(
            "TMDB request timed out. Please try again."
        ) from error

    except requests.exceptions.RequestException as error:
        raise TMDBAPIError(
            "Unable to connect to TMDB. Check your internet connection."
        ) from error

    except ValueError as error:
        raise TMDBAPIError(
            "TMDB returned an invalid response."
        ) from error


# --------------------------------------------------
# MOVIE SEARCH
# --------------------------------------------------

def search_movies(
    query,
    region=DEFAULT_REGION,
    language=DEFAULT_LANGUAGE,
    page=1
):
    """
    Search for movies using their titles.

    Returns a list of movie dictionaries.
    """

    if not isinstance(query, str) or not query.strip():
        return []

    if not isinstance(page, int) or isinstance(page, bool) or page < 1:
        raise ValueError("Page must be a positive integer.")

    data = _make_request(
        "search/movie",
        params={
            "query": query.strip(),
            "region": region,
            "language": language,
            "include_adult": False,
            "page": page
        }
    )

    return data.get("results", [])


# --------------------------------------------------
# MOVIE DETAILS
# --------------------------------------------------

def get_movie_details(
    tmdb_id,
    language=DEFAULT_LANGUAGE
):
    """
    Retrieve movie details, cast, crew, videos and images.

    Credits, videos and images are included in one request.
    """

    data = _make_request(
        f"movie/{tmdb_id}",
        params={
            "language": language,
            "append_to_response": "credits,videos,images"
        }
    )

    return data


def get_movie_credits(tmdb_id, language=DEFAULT_LANGUAGE):
    """Retrieve movie cast and crew."""

    return _make_request(
        f"movie/{tmdb_id}/credits",
        params={"language": language}
    )


def get_movie_videos(tmdb_id, language=DEFAULT_LANGUAGE):
    """Retrieve trailers and other movie videos."""

    data = _make_request(
        f"movie/{tmdb_id}/videos",
        params={"language": language}
    )

    return data.get("results", [])


def get_movie_images(tmdb_id):
    """Retrieve movie posters and backdrops."""

    return _make_request(
        f"movie/{tmdb_id}/images"
    )


# --------------------------------------------------
# ACTOR AND DIRECTOR SEARCH
# --------------------------------------------------

def search_people(
    query,
    language=DEFAULT_LANGUAGE,
    page=1
):
    """Search for actors, directors and other film professionals."""

    if not isinstance(query, str) or not query.strip():
        return []

    if not isinstance(page, int) or isinstance(page, bool) or page < 1:
        raise ValueError("Page must be a positive integer.")

    data = _make_request(
        "search/person",
        params={
            "query": query.strip(),
            "language": language,
            "include_adult": False,
            "page": page
        }
    )

    return data.get("results", [])


def get_person_movie_credits(
    person_id,
    language=DEFAULT_LANGUAGE
):
    """Retrieve movies associated with an actor or director."""

    return _make_request(
        f"person/{person_id}/movie_credits",
        params={"language": language}
    )


# --------------------------------------------------
# INDIAN STREAMING AVAILABILITY
# --------------------------------------------------

def get_movie_watch_providers(
    tmdb_id,
    region=DEFAULT_REGION
):
    """
    Retrieve streaming, rental and purchase providers.

    Provider categories may include:
    - flatrate: Subscription
    - free: Free
    - ads: Free with advertisements
    - rent: Rental
    - buy: Purchase

    Actual availability depends on the returned provider data.
    """

    data = _make_request(
        f"movie/{tmdb_id}/watch/providers"
    )

    results = data.get("results", {})

    return {
        "region": region.upper(),
        "availability": results.get(region.upper()),
        "attribution": WATCH_PROVIDER_ATTRIBUTION
    }


# --------------------------------------------------
# TMDB IMAGE URL GENERATION
# --------------------------------------------------

TMDB_IMAGE_BASE_URL = "https://image.tmdb.org/t/p/"

VALID_IMAGE_SIZES = {
    "w45",
    "w92",
    "w154",
    "w185",
    "w300",
    "w342",
    "w500",
    "w780",
    "w1280",
    "h632",
    "original",
}


def get_image_url(image_path, image_size="w500"):
    """
    Generate a TMDB image URL without an additional API request.

    Returns None when the image path is unavailable.
    """

    if not image_path or not isinstance(image_path, str):
        return None

    image_path = image_path.strip()

    if not image_path:
        return None

    if image_size not in VALID_IMAGE_SIZES:
        raise ValueError(
            f"Unsupported TMDB image size: {image_size}"
        )

    return (
        f"{TMDB_IMAGE_BASE_URL}"
        f"{image_size}/{image_path.lstrip('/')}"
    )


def get_movie_poster(poster_path, size="w500"):
    """Generate a movie poster URL."""

    return get_image_url(poster_path, size)


def get_movie_backdrop(backdrop_path, size="w1280"):
    """Generate a movie backdrop URL."""

    return get_image_url(backdrop_path, size)


def get_person_profile(profile_path, size="w185"):
    """Generate an actor or director profile image URL."""

    return get_image_url(profile_path, size)

