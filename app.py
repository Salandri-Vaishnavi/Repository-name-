
import json
from pathlib import Path
from html import escape

import pandas as pd
import streamlit as st

from src.authentication.auth_service import (
    AuthenticationError,
    authenticate_user,
    register_user,
)

from src.recommendation.tfidf_engine import ContentBasedRecommender

from src.database.user_activity import (
    add_to_watchlist,
    add_tmdb_movie_to_watchlist,
    remove_from_watchlist,
    get_watchlist,
)

from src.services.tmdb_service import (
    TMDBAPIError,
    search_movies,
    get_movie_details,
    get_movie_poster,
    get_movie_backdrop,
    get_movie_watch_providers,
)


# =====================================================
# PAGE CONFIGURATION
# =====================================================

st.set_page_config(
    page_title="CineMatch AI | Movie Discovery",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="collapsed",
)

BASE_DIR = Path(__file__).resolve().parent
CSS_FILE = BASE_DIR / "assets" / "style.css"
MOVIES_FILE = BASE_DIR / "data" / "processed" / "processed_movies.csv"


# =====================================================
# SESSION STATE
# =====================================================

if "user" not in st.session_state:
    st.session_state.user = None

if "selected_movie" not in st.session_state:
    st.session_state.selected_movie = None

if "recommendation_results" not in st.session_state:
    st.session_state.recommendation_results = None

if "recommendation_source_title" not in st.session_state:
    st.session_state.recommendation_source_title = None


# =====================================================
# LOAD CSS
# =====================================================

if CSS_FILE.exists():
    st.markdown(
        f"<style>{CSS_FILE.read_text(encoding='utf-8')}</style>",
        unsafe_allow_html=True,
    )


st.markdown(
    """
    <style>
    .movie-card {
        background: linear-gradient(145deg, #191d38, #101225);
        border: 1px solid rgba(255,255,255,0.09);
        border-radius: 15px;
        padding: 17px;
        min-height: 215px;
        margin-bottom: 18px;
        transition: 0.25s ease;
    }

    .movie-card:hover {
        transform: translateY(-4px);
        border-color: #9561ff;
        box-shadow: 0 10px 28px rgba(100,70,200,0.2);
    }

    .movie-poster {
        width: 100%;
        aspect-ratio: 2 / 3;
        height: auto;
        overflow: hidden;
        border-radius: 11px;
        margin-bottom: 14px;
        display: flex;
        justify-content: center;
        align-items: center;
        background:
            radial-gradient(circle at 20% 20%,
                rgba(177,138,255,0.4), transparent 45%),
            linear-gradient(135deg, #29224f, #142c49);
    }

    .movie-poster img {
        width: 100%;
        height: 100%;
        object-fit: cover;
        display: block;
    }

    .movie-poster span {
        font-size: 38px;
    }

    .movie-title {
        color: #ffffff;
        font-size: 15px;
        font-weight: 700;
        line-height: 1.4;
        min-height: 42px;
        margin-bottom: 8px;
    }

    .movie-meta {
        color: #b0b2ca;
        font-size: 12px;
        line-height: 1.7;
    }

    .movie-rating {
        color: #ffd36b;
        font-weight: 700;
    }

    .section-heading {
        color: #ffffff;
        font-size: 23px;
        font-weight: 800;
        margin-top: 22px;
        margin-bottom: 5px;
    }

    .section-description {
        color: #a2a5bd;
        font-size: 13px;
        margin-bottom: 18px;
    }

    .dashboard-hero {
        padding: 32px;
        border-radius: 20px;
        margin-bottom: 25px;
        background:
            radial-gradient(circle at 85% 15%,
                rgba(40,217,240,0.16), transparent 35%),
            linear-gradient(120deg, #29204d, #11152c 75%);
        border: 1px solid rgba(255,255,255,0.10);
    }

    .dashboard-hero h1 {
        font-size: 36px;
        font-weight: 900;
        color: white;
        letter-spacing: -1px;
    }

    .dashboard-hero p {
        color: #c0c0d5;
        font-size: 14px;
    }

    .score-pill {
        color: #cbb4ff;
        background: rgba(149,97,255,0.15);
        border: 1px solid rgba(149,97,255,0.25);
        border-radius: 20px;
        padding: 5px 9px;
        font-size: 11px;
        font-weight: 700;
        display: inline-block;
        margin-top: 8px;
    }

    .top-space {
        height: 10px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# =====================================================
# DATA LOADING
# =====================================================

@st.cache_data
def load_movies():

    if not MOVIES_FILE.exists():
        raise FileNotFoundError(
            f"Movie dataset not found: {MOVIES_FILE}"
        )

    movies = pd.read_csv(MOVIES_FILE)

    movies["average_rating"] = pd.to_numeric(
        movies["average_rating"], errors="coerce"
    ).fillna(0)

    movies["rating_count"] = pd.to_numeric(
        movies["rating_count"], errors="coerce"
    ).fillna(0)

    movies["year"] = pd.to_numeric(
        movies["year"], errors="coerce"
    )

    movies["genres"] = movies["genres"].fillna(
        "(No genres listed)"
    )

    links_file = (
        BASE_DIR / "data" / "raw" / "ml-latest-small" / "links.csv"
    )

    if links_file.exists():

        links = pd.read_csv(links_file)

        links["tmdbId"] = pd.to_numeric(
            links["tmdbId"], errors="coerce"
        )

        links = links.dropna(subset=["tmdbId"])
        links["tmdbId"] = links["tmdbId"].astype(int)

        movies["movieId"] = pd.to_numeric(
            movies["movieId"], errors="coerce"
        )

        movies = movies.merge(
            links[["movieId", "tmdbId"]],
            on="movieId",
            how="left",
        )

        movies = movies.rename(
            columns={"tmdbId": "tmdb_id"}
        )

    else:
        movies["tmdb_id"] = pd.NA

    return movies


@st.cache_resource
def get_recommender():

    recommender = ContentBasedRecommender()
    recommender.load_data()
    recommender.train()

    return recommender


@st.cache_data(ttl=86400, show_spinner=False)
def get_cached_movie_details(tmdb_id):
    return get_movie_details(int(tmdb_id))


@st.cache_data(ttl=21600, show_spinner=False)
def get_cached_movie_watch_providers(tmdb_id):
    return get_movie_watch_providers(int(tmdb_id))


@st.cache_data(ttl=300, show_spinner=False)
def load_verified_movie_sources():

    source_file = BASE_DIR / "data" / "verified_movie_sources.json"

    if not source_file.exists():
        return {}

    try:
        with source_file.open("r", encoding="utf-8") as file:
            data = json.load(file)

        return data if isinstance(data, dict) else {}

    except (OSError, json.JSONDecodeError):
        return {}


def _normalise_movie_title(value):

    return "".join(
        character
        for character in str(value or "").casefold()
        if character.isalnum()
    )


def _movie_title_aliases(value):

    title = _normalise_movie_title(value)
    aliases = {title}

    if title in {"seetha", "sita"}:
        aliases.update({"seetha", "sita"})

    return aliases


def _is_valid_verified_source(source):

    return (
        isinstance(source, dict)
        and source.get("verified") is True
        and source.get("type") == "full_movie"
        and isinstance(source.get("url"), str)
        and source["url"].startswith("https://")
    )


def get_verified_movie_source(
    tmdb_id=None,
    title=None,
    year=None,
):

    sources = load_verified_movie_sources()

    if tmdb_id is not None and not pd.isna(tmdb_id):

        source = sources.get(str(int(tmdb_id)))

        if _is_valid_verified_source(source):
            return source

    if title and year is not None and not pd.isna(year):

        requested_year = int(year)
        requested_aliases = _movie_title_aliases(title)

        key = (
            f"title:{str(title).strip().casefold()}|"
            f"year:{requested_year}"
        )

        source = sources.get(key)

        if _is_valid_verified_source(source):
            return source

        for candidate in sources.values():

            if not _is_valid_verified_source(candidate):
                continue

            candidate_year = candidate.get("year")

            if candidate_year is None:
                continue

            if (
                int(candidate_year) == requested_year
                and requested_aliases
                & _movie_title_aliases(candidate.get("title", ""))
            ):
                return candidate

    return None


@st.cache_data(show_spinner=False)
def get_tmdb_id_map():

    movies = load_movies()
    mapping = {}

    for row in movies[
        ["movieId", "tmdb_id"]
    ].itertuples(index=False):

        if pd.notna(row.tmdb_id):
            mapping[int(row.movieId)] = int(row.tmdb_id)

    return mapping


# =====================================================
# BRAND
# =====================================================

def display_brand():

    st.markdown(
        """
        <div class="brand-name">
            CineMatch <span class="brand-highlight">AI</span>
        </div>
        <div class="brand-tagline">
            YOUR TASTE. YOUR MOVIES. YOUR MATCH.
        </div>
        """,
        unsafe_allow_html=True,
    )


# =====================================================
# MOVIE CARD
# =====================================================

def display_movie_card(
    movie,
    show_similarity=False,
    show_watchlist_action=False,
    card_context="default",
):

    title_value = str(movie.get("title", "Untitled Movie"))
    title = escape(title_value)

    genres = escape(
        str(movie.get("genres", "Unknown")).replace("|", " · ")
    )

    try:
        rating = float(movie.get("average_rating", 0) or 0)
    except (TypeError, ValueError):
        rating = 0.0

    year = movie.get("year", movie.get("release_year"))

    year_text = (
        str(int(year))
        if year is not None and pd.notna(year)
        else "Year unavailable"
    )

    try:
        rating_count = int(movie.get("rating_count", 0) or 0)
    except (TypeError, ValueError):
        rating_count = 0

    movie_id = movie.get("movieId", movie.get("movie_id"))
    tmdb_id = movie.get("tmdb_id")

    if (tmdb_id is None or pd.isna(tmdb_id)) and (
        movie_id is not None and pd.notna(movie_id)
    ):
        tmdb_id = get_tmdb_id_map().get(int(movie_id))

    if tmdb_id is not None and pd.notna(tmdb_id):
        tmdb_id = int(tmdb_id)
    else:
        tmdb_id = None

    poster_url = movie.get("poster_url")

    if (
        not isinstance(poster_url, str)
        or not poster_url.startswith("https://")
    ):
        poster_url = None

    details = None

    if tmdb_id is not None:

        try:

            details = get_cached_movie_details(tmdb_id)

            if not poster_url:

                poster_path = details.get("poster_path")

                if not poster_path:

                    posters = details.get(
                        "images", {}
                    ).get("posters", [])

                    if posters:
                        poster_path = posters[0].get("file_path")

                poster_url = get_movie_poster(poster_path)

        except TMDBAPIError:
            details = None

    if poster_url:

        poster_html = f"""
            <div class="movie-poster">
                <img src="{escape(poster_url, quote=True)}"
                     alt="{title} poster" loading="lazy">
            </div>
        """

    else:

        poster_html = """
            <div class="movie-poster"><span>🎬</span></div>
        """

    similarity = movie.get("similarity_score")
    score_html = ""

    if (
        show_similarity
        and similarity is not None
        and pd.notna(similarity)
    ):

        score_html = f"""
            <div class="score-pill">
                AI similarity: {float(similarity):.1f}%
            </div>
        """

    st.html(
        f"""
        <div class="movie-card">
            {poster_html}
            <div class="movie-title">{title}</div>
            <div class="movie-meta">
                {year_text}<br>
                <span class="movie-rating">★ {rating:.1f}/5</span>
                &nbsp; · &nbsp; {rating_count:,} ratings<br>
                {genres}
            </div>
            {score_html}
        </div>
        """
    )

    source = get_verified_movie_source(
        tmdb_id=tmdb_id,
        title=title_value,
        year=year if year is not None and pd.notna(year) else None,
    )

    if source:

        provider = escape(
            str(source.get("provider") or "Official provider")
        )

        st.link_button(
            f"▶ Watch Full Movie · {provider}",
            source["url"],
            use_container_width=True,
        )

    else:

        st.caption(
            "No verified complete-movie link is currently available."
        )

    if tmdb_id is not None:

        try:

            provider_data = get_cached_movie_watch_providers(tmdb_id)

            availability = provider_data.get("availability") or {}
            provider_link = availability.get("link")

            categories = [
                ("free", "Free"),
                ("ads", "Ad-supported"),
                ("flatrate", "Subscription"),
                ("rent", "Rent"),
                ("buy", "Buy"),
            ]

            available_options = []

            for category_key, category_label in categories:

                providers = availability.get(category_key, [])

                if providers:

                    provider_names = [
                        item.get("provider_name", "Unknown")
                        for item in providers
                    ]

                    available_options.append(
                        f"{category_label}: {', '.join(provider_names)}"
                    )

            if available_options:

                st.markdown("**📺 Streaming availability**")

                for option in available_options:
                    st.caption(option)

            if provider_link:

                st.link_button(
                    "Check streaming availability",
                    provider_link,
                    use_container_width=True,
                )

                st.caption(
                    "This opens a provider-listing page; it does not "
                    "guarantee direct playback or a free full movie."
                )

            elif not available_options:

                st.caption(
                    "Streaming availability is not currently listed for India."
                )

            st.caption(
                provider_data.get(
                    "attribution",
                    "Streaming availability data provided by JustWatch.",
                )
            )

        except TMDBAPIError:

            st.caption(
                "Streaming availability could not be loaded right now."
            )

    context_key = _normalise_movie_title(card_context) or "default"

    action_key = (
        f"{tmdb_id or _normalise_movie_title(title_value)}_"
        f"{'similarity' if show_similarity else 'standard'}_"
        f"{'watchlist' if show_watchlist_action else 'view'}_"
        f"{context_key}"
    )

    if tmdb_id is not None:

        if st.button(
            "⬇ Download options",
            key=f"download_info_{action_key}",
            use_container_width=True,
        ):

            st.info(
                "CineMatch does not download copyrighted movies. "
                "If your streaming provider supports offline viewing, "
                "use its official app and follow its terms."
            )

    if show_watchlist_action:

        if movie_id is not None and pd.notna(movie_id):

            movie_id = int(movie_id)
            user_id = st.session_state.user["user_id"]

            if st.button(
                "❤️ Add to Watchlist",
                key=(
                    f"add_watchlist_{movie_id}_"
                    f"{'recommendation' if show_similarity else 'explorer'}"
                ),
                use_container_width=True,
            ):

                try:

                    added = add_to_watchlist(
                        user_id,
                        movie_id,
                    )

                    if added:
                        st.success("Movie added to your watchlist!")
                    else:
                        st.info("This movie is already in your watchlist.")

                except Exception:
                    st.error("Unable to update your watchlist.")


# =====================================================
# MOVIE COLLECTION
# =====================================================

def display_movie_collection(
    heading,
    description,
    movies,
    show_similarity=False,
    limit=8,
):

    st.markdown(
        f"""
        <div class="section-heading">{escape(heading)}</div>
        <div class="section-description">
            {escape(description)}
        </div>
        """,
        unsafe_allow_html=True,
    )

    if movies.empty:
        st.info("No movies available in this collection.")
        return

    selected_movies = movies.head(limit)
    columns = st.columns(4)

    for index, (_, movie) in enumerate(selected_movies.iterrows()):

        with columns[index % 4]:

            display_movie_card(
                movie,
                show_similarity=show_similarity,
                card_context=heading,
            )


# =====================================================
# LOGIN
# =====================================================

def display_login_form():

    with st.form("login_form"):

        identifier = st.text_input(
            "Username or Email",
            placeholder="Enter your username or email",
        )

        password = st.text_input(
            "Password",
            type="password",
            placeholder="Enter your password",
        )

        submitted = st.form_submit_button(
            "Sign In →",
            use_container_width=True,
        )

        if submitted:

            if not identifier.strip() or not password:

                st.error("Please enter your login details.")

            else:

                try:

                    user = authenticate_user(
                        identifier.strip(),
                        password,
                    )

                    if user:

                        st.session_state.user = user
                        st.rerun()

                    else:

                        st.error("Invalid login credentials.")

                except AuthenticationError as error:

                    st.error(str(error))

                except Exception:

                    st.error("Unable to sign in. Please try again.")


# =====================================================
# REGISTRATION
# =====================================================

def display_registration_form():

    with st.form("registration_form"):

        full_name = st.text_input(
            "Full Name",
            placeholder="Your full name",
        )

        username = st.text_input(
            "Username",
            placeholder="Choose a username",
        )

        email = st.text_input(
            "Email Address",
            placeholder="Your email address",
        )

        password = st.text_input(
            "Password",
            type="password",
            placeholder="Create a password",
        )

        confirm_password = st.text_input(
            "Confirm Password",
            type="password",
            placeholder="Confirm your password",
        )

        submitted = st.form_submit_button(
            "Create Account →",
            use_container_width=True,
        )

        if submitted:

            if not all([
                full_name.strip(),
                username.strip(),
                email.strip(),
                password,
                confirm_password,
            ]):

                st.error("Please complete all fields.")

            elif password != confirm_password:

                st.error("Passwords do not match.")

            else:

                try:

                    register_user(
                        username=username,
                        email=email,
                        password=password,
                        full_name=full_name,
                    )

                    st.success(
                        "Account created successfully. Please sign in."
                    )

                except (ValueError, AuthenticationError) as error:

                    st.error(str(error))

                except Exception:

                    st.error(
                        "Unable to create your account. "
                        "Please try again."
                    )


# =====================================================
# AUTHENTICATION PAGE
# =====================================================

def display_authentication_page():

    left, right = st.columns(
        [1.15, 0.85],
        gap="large",
    )

    with left:

        display_brand()

        st.html(
            """
            <div class="dashboard-hero">
                <div style="
                    color:#d5baff;
                    font-size:12px;
                    font-weight:700;
                    letter-spacing:1.5px;
                    margin-bottom:20px;">
                    ✦ AI-POWERED MOVIE DISCOVERY
                </div>

                <h1>
                    Every movie has<br>
                    <span style="
                        background:linear-gradient(
                            100deg,#b18aff,#28d9f0
                        );
                        -webkit-background-clip:text;
                        -webkit-text-fill-color:transparent;">
                        a match.
                    </span>
                </h1>

                <p>
                    Discover movies that match your interests.
                    Explore new favourites and enjoy intelligent
                    movie recommendations.
                </p>

                <p>✨ Personalized Discovery</p>
                <p>🎬 Smart Recommendations</p>
                <p>❤️ Your Watchlist</p>
            </div>
            """
        )

    with right:

        st.markdown(
            """
            <div class="auth-heading">
                Welcome to CineMatch
            </div>
            <div class="auth-subtitle">
                Your next favourite movie is just a match away.
            </div>
            """,
            unsafe_allow_html=True,
        )

        login_tab, register_tab = st.tabs(
            ["Sign In", "Create Account"]
        )

        with login_tab:
            display_login_form()

        with register_tab:
            display_registration_form()


# =====================================================
# HOME DASHBOARD HELPERS
# =====================================================

def _get_source_tmdb_id(source_key, source):

    candidate = source.get("tmdb_id")

    if candidate is not None:

        try:
            return int(candidate)

        except (TypeError, ValueError):
            pass

    if str(source_key).isdigit():
        return int(source_key)

    return None


def _find_tmdb_search_match(source):

    try:
        results = search_movies(str(source.get("title", "")))

    except TMDBAPIError:
        return None

    source_year = source.get("year")
    wanted_titles = _movie_title_aliases(source.get("title", ""))

    for item in results:

        release_date = item.get("release_date") or ""

        result_year = (
            int(release_date[:4])
            if len(release_date) >= 4 and release_date[:4].isdigit()
            else None
        )

        if result_year != int(source_year):
            continue

        if not (
            wanted_titles & _movie_title_aliases(item.get("title", ""))
        ):
            continue

        return item

    return None


def get_featured_watchable_movies(movies, limit=12):

    sources = load_verified_movie_sources()

    featured = []
    seen = set()

    for source_key, source in sources.items():

        if not _is_valid_verified_source(source):
            continue

        title = str(source.get("title") or "").strip()
        source_year = source.get("year")

        if not title or source_year is None:
            continue

        try:
            source_year = int(source_year)

        except (TypeError, ValueError):
            continue

        tmdb_id = _get_source_tmdb_id(source_key, source)
        wanted_titles = _movie_title_aliases(title)

        local_match = None

        for _, row in movies.iterrows():

            row_year = row.get("year")

            if row_year is None or pd.isna(row_year):
                continue

            if int(row_year) != source_year:
                continue

            if wanted_titles & _movie_title_aliases(row.get("title", "")):
                local_match = row.to_dict()
                break

        if local_match:

            if tmdb_id is None:

                local_tmdb_id = local_match.get("tmdb_id")

                if local_tmdb_id is not None and pd.notna(local_tmdb_id):
                    tmdb_id = int(local_tmdb_id)

            movie = local_match
            movie["tmdb_id"] = tmdb_id
            movie["year"] = source_year

            poster_url = movie.get("poster_url")

        else:

            item = _find_tmdb_search_match(source)

            if not item:

                if tmdb_id is None:
                    continue

                try:
                    details = get_cached_movie_details(tmdb_id)

                except TMDBAPIError:
                    continue

                release_date = details.get("release_date") or ""

                details_year = (
                    int(release_date[:4])
                    if len(release_date) >= 4 and release_date[:4].isdigit()
                    else None
                )

                if details_year != source_year:
                    continue

                item = details

            tmdb_id = int(item.get("id") or tmdb_id or 0) or None

            poster_url = get_movie_poster(item.get("poster_path"))

            movie = {
                "movieId": None,
                "tmdb_id": tmdb_id,
                "title": item.get("title") or title,
                "year": source_year,
                "genres": "",
                "average_rating": float(item.get("vote_average") or 0) / 2,
                "rating_count": int(item.get("vote_count") or 0),
                "overview": item.get("overview") or "",
                "poster_url": poster_url,
                "source": "verified_source",
            }

        if not poster_url and tmdb_id is not None:

            try:

                details = get_cached_movie_details(tmdb_id)
                poster_url = get_movie_poster(details.get("poster_path"))
                movie["poster_url"] = poster_url

            except TMDBAPIError:
                poster_url = None

        if (
            not isinstance(poster_url, str)
            or not poster_url.startswith("https://")
        ):
            continue

        dedupe_key = (
            tmdb_id,
            _normalise_movie_title(title),
            source_year,
            source.get("url"),
        )

        if dedupe_key in seen:
            continue

        seen.add(dedupe_key)
        featured.append(movie)

        if len(featured) >= limit:
            break

    return pd.DataFrame(featured)


# =====================================================
# HOME
# =====================================================

def display_home(movies):

    user = st.session_state.user

    first_name = (
        user.get("full_name")
        or user.get("username")
        or "Movie Lover"
    )

    st.html(
        f"""
        <div class="dashboard-hero">
            <div style="
                color:#d5baff;
                font-size:12px;
                font-weight:700;
                letter-spacing:1.5px;">
                WELCOME BACK
            </div>
            <h1>Hello, {escape(str(first_name))} 👋</h1>
            <p>
                Find your next favourite movie.
                Your movie discovery journey starts here.
            </p>
        </div>
        """
    )

    watchable_movies = get_featured_watchable_movies(movies)

    if watchable_movies.empty:

        st.markdown(
            '<div class="section-heading">🎬 Watch Full Movies</div>',
            unsafe_allow_html=True,
        )

        st.info(
            "No complete-movie links have been verified yet. "
            "Once a movie source is checked and marked verified in "
            "data/verified_movie_sources.json, it will appear here "
            "when its poster is available."
        )

    else:

        display_movie_collection(
            "🎬 Watch Full Movies",
            "Complete films with a reviewed viewing link and an available poster.",
            watchable_movies,
            limit=12,
        )

    st.divider()

    popular = movies.sort_values(
        by=["rating_count", "average_rating"],
        ascending=False,
    )

    display_movie_collection(
        "🔥 Popular Movies",
        "Movies with the highest number of user ratings.",
        popular,
    )

    st.divider()

    top_rated = movies[
        movies["rating_count"] >= 50
    ].sort_values(
        by=["average_rating", "rating_count"],
        ascending=[False, False],
    )

    display_movie_collection(
        "⭐ Top Rated Movies",
        "Highly rated movies with a reasonable number of ratings.",
        top_rated,
    )

    st.divider()

    recent = movies[
        movies["rating_count"] >= 10
    ].sort_values(
        by=["year", "rating_count"],
        ascending=[False, False],
        na_position="last",
    )

    display_movie_collection(
        "🆕 Recently Released",
        "Explore newer movies available in our catalogue.",
        recent,
    )


# =====================================================
# MOVIE EXPLORER
# =====================================================

def display_movie_explorer(movies):

    st.markdown("## 🔎 Movie Explorer")

    st.write(
        "Search the movie catalogue and discover movies by genre."
    )

    search_text = st.text_input(
        "Search movies",
        placeholder="Enter a movie title...",
        key="explorer_search",
    )

    all_genres = sorted({
        genre.strip()
        for value in movies["genres"].dropna()
        for genre in str(value).split("|")
        if genre.strip()
        and genre.strip() != "(no genres listed)"
    })

    selected_genre = st.selectbox(
        "Filter by genre",
        ["All Genres"] + all_genres,
        key="explorer_genre",
    )

    if search_text.strip():

        local_results = movies[
            movies["title"].str.contains(
                search_text.strip(),
                case=False,
                na=False,
                regex=False,
            )
        ].copy()

        try:

            with st.spinner("Searching the movie catalogue..."):
                tmdb_results = search_movies(search_text.strip())

        except TMDBAPIError:

            tmdb_results = []

            st.warning(
                "Online movie search is temporarily unavailable. "
                "Showing local catalogue results."
            )

        local_results["source"] = "local"

        local_tmdb_ids = set()

        if "tmdb_id" in local_results.columns:

            local_tmdb_ids = {
                int(value)
                for value in local_results["tmdb_id"].dropna()
            }

        external_results = []

        for item in tmdb_results:

            tmdb_id = item.get("id")

            if not tmdb_id or tmdb_id in local_tmdb_ids:
                continue

            release_date = item.get("release_date") or ""

            external_results.append({
                "movieId": None,
                "tmdb_id": int(tmdb_id),
                "title": item.get("title") or "Untitled Movie",
                "year": (
                    int(release_date[:4])
                    if len(release_date) >= 4
                    and release_date[:4].isdigit()
                    else None
                ),
                "genres": "",
                "average_rating": (
                    float(item.get("vote_average") or 0) / 2
                ),
                "rating_count": int(item.get("vote_count") or 0),
                "overview": item.get("overview") or "",
                "poster_url": (
                    get_movie_poster(item.get("poster_path"))
                    if item.get("poster_path")
                    else None
                ),
                "source": "tmdb",
                "tmdb_data": {
                    **item,
                    "poster_url": (
                        get_movie_poster(item.get("poster_path"))
                        if item.get("poster_path")
                        else None
                    ),
                    "backdrop_url": (
                        get_movie_backdrop(
                            item.get("backdrop_path"),
                            size="w780",
                        )
                        if item.get("backdrop_path")
                        else None
                    ),
                },
            })

        st.markdown("### 📚 Local Catalogue")

        if not local_results.empty:

            if selected_genre != "All Genres":

                local_results = local_results[
                    local_results["genres"].str.contains(
                        selected_genre,
                        case=False,
                        na=False,
                        regex=False,
                    )
                ]

            local_results = local_results.sort_values(
                by=["average_rating", "rating_count"],
                ascending=False,
            )

            st.caption(
                f"{len(local_results):,} local matches"
            )

            for start in range(0, min(len(local_results), 40), 4):

                columns = st.columns(4)

                for index, (_, movie) in enumerate(
                    local_results.iloc[start:start + 4].iterrows()
                ):

                    with columns[index]:

                        display_movie_card(
                            movie,
                            show_watchlist_action=True,
                            card_context="explorer",
                        )

        else:

            st.info("No matching movies in the local catalogue.")

        st.markdown("### 🌐 More Movies from TMDB")

        if selected_genre != "All Genres":

            st.caption(
                "Genre filtering currently applies to local catalogue results."
            )

        if external_results:

            st.caption(
                f"{len(external_results)} additional online matches"
            )

            for start in range(0, min(len(external_results), 20), 4):

                columns = st.columns(4)

                for index, movie in enumerate(
                    external_results[start:start + 4]
                ):

                    with columns[index]:

                        display_movie_card(
                            movie,
                            show_watchlist_action=False,
                            card_context="tmdb_explorer",
                        )

                        if st.button(
                            "❤️ Add to Watchlist",
                            key=f"tmdb_explorer_add_{movie['tmdb_id']}",
                            use_container_width=True,
                        ):

                            try:

                                added = add_tmdb_movie_to_watchlist(
                                    st.session_state.user["user_id"],
                                    movie["tmdb_data"],
                                )

                                if added:
                                    st.success(
                                        "Movie added to your watchlist!"
                                    )
                                else:
                                    st.info(
                                        "This movie is already in your watchlist."
                                    )

                            except Exception as error:

                                st.error(
                                    "Unable to update your watchlist."
                                )

                                st.exception(error)

        else:

            st.info("No additional online matches found.")

    else:

        st.info(
            "Enter a movie title to search the local catalogue "
            "and discover more movies online."
        )

        if selected_genre != "All Genres":

            filtered = movies[
                movies["genres"].str.contains(
                    selected_genre,
                    case=False,
                    na=False,
                    regex=False,
                )
            ]

        else:

            filtered = movies.copy()

        filtered = filtered.sort_values(
            by=["average_rating", "rating_count"],
            ascending=False,
        )

        st.caption(
            f"Showing {len(filtered):,} movies."
        )

        for start in range(0, min(len(filtered), 40), 4):

            columns = st.columns(4)

            for index, (_, movie) in enumerate(
                filtered.iloc[start:start + 4].iterrows()
            ):

                with columns[index]:

                    display_movie_card(
                        movie,
                        show_watchlist_action=True,
                        card_context="explorer",
                    )


# =====================================================
# AI RECOMMENDATION STUDIO
# =====================================================

def display_recommendation_studio(movies):

    st.markdown("## ✨ AI Recommendation Studio")

    st.write(
        "Choose a movie you enjoy. CineMatch AI will find "
        "similar movies using content-based filtering."
    )

    movie_titles = sorted(
        movies["title"].dropna().unique().tolist()
    )

    search_title = st.text_input(
        "Find a movie",
        placeholder="Search for a movie title...",
        key="recommendation_search",
    )

    if search_title.strip():

        matching_titles = [
            title
            for title in movie_titles
            if search_title.lower() in title.lower()
        ]

    else:

        matching_titles = movie_titles

    if not matching_titles:

        st.warning("No matching movie titles found.")
        return

    selected_title = st.selectbox(
        "Select a movie",
        matching_titles[:200],
        key="recommendation_movie",
    )

    top_n = st.slider(
        "Number of recommendations",
        min_value=5,
        max_value=20,
        value=10,
        key="recommendation_count",
    )

    if st.button(
        "Find My Movie Matches ✨",
        use_container_width=True,
    ):

        try:

            with st.spinner(
                "Analyzing movie content and finding matches..."
            ):

                recommender = get_recommender()

                results = recommender.recommend(
                    selected_title,
                    top_n=top_n,
                )

            if results is None or results.empty:

                st.session_state["recommendation_results"] = None

                st.warning(
                    "No recommendations were found for this movie."
                )

            else:

                st.session_state["recommendation_results"] = (
                    results.copy()
                )

                st.session_state["recommendation_source_title"] = (
                    selected_title
                )

                st.success(
                    f"Found {len(results)} recommendations "
                    f"similar to {selected_title}."
                )

        except Exception as error:

            st.session_state["recommendation_results"] = None

            st.error(
                "Unable to generate recommendations. "
                "Please check the movie selection and try again."
            )

            st.exception(error)

    results = st.session_state.get("recommendation_results")

    if results is not None and not results.empty:

        source_title = st.session_state.get(
            "recommendation_source_title",
            "your selected movie",
        )

        st.markdown("### 🎯 Your Movie Matches")

        st.caption(
            f"Movies similar to {source_title}"
        )

        for start in range(0, len(results), 4):

            columns = st.columns(4)
            batch = results.iloc[start:start + 4]

            for index, (_, movie) in enumerate(batch.iterrows()):

                with columns[index]:

                    display_movie_card(
                        movie,
                        show_similarity=True,
                        show_watchlist_action=True,
                        card_context="recommendations",
                    )

                    st.caption(
                        str(movie["explanation"])
                    )


# =====================================================
# WATCHLIST
# =====================================================

def display_watchlist():

    user = st.session_state.user
    user_id = user["user_id"]

    st.markdown("## ❤️ My Watchlist")

    st.write(
        "Your personally saved collection of movies. "
        "Keep track of the movies you want to watch."
    )

    try:

        watchlist = get_watchlist(user_id)

        if not watchlist:

            st.info(
                "Your watchlist is empty. "
                "Explore movies and add your favourite movies!"
            )

            return

        st.success(
            f"You have saved {len(watchlist)} movies."
        )

        for start in range(0, len(watchlist), 4):

            columns = st.columns(4)
            batch = watchlist[start:start + 4]

            for index, movie in enumerate(batch):

                movie = dict(movie)

                with columns[index]:

                    movie_id = int(movie["movie_id"])

                    tmdb_id = None

                    if movie_id >= 1_000_000_000:
                        tmdb_id = movie_id - 1_000_000_000

                    movie_card_data = {
                        "movie_id": movie_id,
                        "movieId": (
                            None if tmdb_id is not None else movie_id
                        ),
                        "tmdb_id": tmdb_id,
                        "title": movie["title"],
                        "year": movie.get("release_year"),
                        "genres": movie.get("genres") or "Unknown",
                        "average_rating": movie.get("average_rating", 0),
                        "rating_count": movie.get("rating_count", 0),
                        "poster_url": movie.get("poster_url"),
                        "overview": movie.get("overview", ""),
                    }

                    display_movie_card(
                        movie_card_data,
                        card_context="watchlist",
                    )

                    if st.button(
                        "🗑️ Remove from Watchlist",
                        key=f"remove_watchlist_{movie_id}",
                        use_container_width=True,
                    ):

                        removed = remove_from_watchlist(
                            user_id,
                            movie_id,
                        )

                        if removed:

                            st.success(
                                "Movie removed from your watchlist!"
                            )

                            st.rerun()

                        else:

                            st.warning(
                                "Movie was not found in your watchlist."
                            )

    except Exception as error:

        st.error("Unable to load your watchlist.")
        st.exception(error)


# =====================================================
# PROFILE - ACCOUNT INFORMATION ONLY
# =====================================================

def display_profile():

    user = st.session_state.user

    st.markdown("## 👤 My Account")

    st.markdown("### Account Information")

    st.write(
        f"**Name:** {user.get('full_name') or 'Not provided'}"
    )

    st.write(
        f"**Username:** {user.get('username') or 'Not provided'}"
    )

    st.write(
        f"**Email:** {user.get('email') or 'Not provided'}"
    )

    st.caption(
        "Your account is managed securely through CineMatch AI authentication."
    )


# =====================================================
# MAIN DASHBOARD
# =====================================================

def display_dashboard():

    try:

        movies = load_movies()

    except Exception as error:

        st.error("Unable to load the movie catalogue.")
        st.exception(error)
        return

    # Display the brand once.
    # No profile picture or avatar.

    display_brand()

    st.divider()

    # Display only one navigation bar.

    selected_page = st.radio(
        "Navigation",
        [
            "Home",
            "Movie Explorer",
            "AI Recommendation Studio",
            "My Watchlist",
            "My Profile",
        ],
        horizontal=True,
        label_visibility="collapsed",
        key="main_dashboard_navigation",
    )

    # Render only the selected page.

    if selected_page == "Home":

        display_home(movies)

    elif selected_page == "Movie Explorer":

        display_movie_explorer(movies)

    elif selected_page == "AI Recommendation Studio":

        display_recommendation_studio(movies)

    elif selected_page == "My Watchlist":

        display_watchlist()

    elif selected_page == "My Profile":

        display_profile()

    st.divider()

    st.caption(
        "© 2026 CineMatch AI · Your Taste. Your Movies. Your Match."
    )

    if st.button(
        "Sign Out",
        key="dashboard_signout",
    ):

        st.session_state.user = None
        st.session_state.pop("main_dashboard_navigation", None)
        st.session_state.pop("recommendation_results", None)
        st.session_state.pop("recommendation_source_title", None)

        st.rerun()


# =====================================================
# APPLICATION ENTRY POINT
# =====================================================

def main():

    if st.session_state.user is None:

        display_authentication_page()

    else:

        display_dashboard()


if __name__ == "__main__":
    main()
