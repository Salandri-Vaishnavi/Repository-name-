**# CineMatch AI 🎬**



**An AI-powered movie discovery and recommendation platform built using Python, Streamlit, and Machine Learning.**



**## Features**



**- User registration and login with bcrypt password hashing.**

**- Movie Explorer for discovering movies.**

**- AI-powered movie recommendations using TF-IDF and cosine similarity.**

**- Personalized recommendations based on user preferences.**

**- Watchlist management with SQLite persistence.**

**- Movie details, posters, and backdrops using TMDB API.**

**- Streaming-provider availability information.**

**- Curated movie collections.**

**- My Profile account information.**



**## Technology Stack**



**| Technology | Purpose |**

**|---|---|**

**| Python | Core programming language |**

**| Streamlit | Web application interface |**

**| Pandas, NumPy | Data processing |**

**| Scikit-learn | Machine learning |**

**| TF-IDF | Movie feature extraction |**

**| Cosine Similarity | Movie similarity |**

**| SQLite | Database |**

**| TMDB API | Movie information |**

**| bcrypt | Password security |**

**| python-dotenv | Environment configuration |**

**| pytest | Automated testing |**



**## Project Structure**



**```text**

**recommendation-system/**

**├── app.py**

**├── requirements.txt**

**├── README.md**

**├── .env.example**

**├── .gitignore**

**├── assets/**

**│   └── style.css**

**├── data/**

**│   ├── raw/**

**│   ├── processed/**

**│   └── verified\_movie\_sources.json**

**├── docs/**

**│   └── architecture.md**

**├── src/**

**│   ├── authentication/**

**│   ├── database/**

**│   ├── evaluation/**

**│   ├── recommendation/**

**│   ├── services/**

**│   └── utils/**

**└── tests/**

**```**



**## Installation and Setup**



**### 1. Clone the repository**



**```bash**

**git clone YOUR\_GITHUB\_REPOSITORY\_URL**

**cd recommendation-system**

**```**



**### 2. Create a virtual environment**



**```bash**

**python -m venv .venv**

**```**



**### 3. Activate the environment**



**```powershell**

**.\\.venv\\Scripts\\Activate.ps1**

**```**



**### 4. Install dependencies**



**```bash**

**pip install -r requirements.txt**

**```**



**### 5. Configure TMDB API**



**Create a `.env` file in the project root:**



**```env**

**TMDB\_READ\_ACCESS\_TOKEN=your\_tmdb\_read\_access\_token**

**```**



**Never upload your actual `.env` file or API token to GitHub.**



**### 6. Run the application**



**```bash**

**python -m streamlit run app.py**

**```**



**Open `http://localhost:8501` in your browser.**



**## Run Tests**



**```bash**

**python -m pytest -v**

**```**



**## Recommendation Methodology**



**1. Movie data is preprocessed.**

**2. TF-IDF converts movie information into numerical feature vectors.**

**3. Cosine similarity measures movie similarity.**

**4. User preferences help generate relevant recommendations.**



**## Dataset**



**The project uses the MovieLens dataset, including movie information, ratings, tags, and links.**



**Please retain the original dataset documentation and attribution when redistributing dataset files.**



**## Third-Party Services**



**- TMDB API provides movie metadata, images, and streaming-provider information.**

**- MovieLens provides movie recommendation data.**



**This product uses the TMDB API but is not endorsed or certified by TMDB.**



**Streaming availability may vary by region and provider. Listings do not guarantee direct movie playback.**



**## Security**



**- API credentials are stored in environment variables.**

**- `.env` files are excluded from Git.**

**- Local SQLite databases are excluded from Git.**

**- Passwords are protected using bcrypt.**



**## Future Improvements**



**- Improve recommendation accuracy.**

**- Expand recommendation evaluation.**

**- Add more personalization capabilities.**

**- Enhance movie discovery.**



**## Developer**



**\*\*CineMatch AI — AI Movie Recommendation System\*\***



**Developed as an AI internship project.**



**---**



**Built with Python, Streamlit, and Machine Learning.**

