**# CineMatch AI – Application Architecture**



**## 1. Overview**



**CineMatch AI is a Streamlit-based movie recommendation platform combining authentication, movie discovery, personalized recommendations, and SQLite database storage.**



**## 2. Application Modules**



**### User Interface**

**- `app.py` – Main Streamlit application.**

**- `assets/style.css` – Application styling.**



**### Authentication**

**- `src/authentication/auth\_service.py` – User authentication functionality.**



**### Database**

**- `src/database/connection.py` – Database connections.**

**- `src/database/schema.py` – Database schema.**

**- `src/database/seed\_movies.py` – Movie data seeding.**

**- `src/database/user\_activity.py` – User activity management.**



**### Recommendation Engine**

**- `src/recommendation/preprocessing.py` – Movie data preprocessing.**

**- `src/recommendation/tfidf\_engine.py` – TF-IDF recommendation functionality.**

**- `src/recommendation/preference\_engine.py` – Preference-based recommendations.**



**### External Services**

**- `src/services/tmdb\_service.py` – TMDB API integration.**



**### Testing**

**- `tests/` – Automated tests for authentication, recommendations, TMDB services, and user activity.**



**## 3. Recommendation Workflow**



**1. Movie information is prepared and processed.**

**2. TF-IDF transforms movie information into feature vectors.**

**3. Cosine similarity measures movie similarity.**

**4. User preferences support personalized recommendations.**

**5. Recommendations are displayed through the Streamlit interface.**



**## 4. Database**



**SQLite provides persistent storage for application data, including user-related information and watchlists.**



**The local database is excluded from the public repository.**



**## 5. TMDB Integration**



**The TMDB service retrieves movie metadata, posters, backdrops, and streaming-provider information.**



**API credentials are loaded from the local `.env` file using `python-dotenv`.**



**## 6. Running the Application**



**```bash**

**python -m streamlit run app.py**

**```**



**The application is accessed locally through the Streamlit URL.**



