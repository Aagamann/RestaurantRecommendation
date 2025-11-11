import pandas as pd
import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# -------------------------------
# 1. Load dataset
# -------------------------------
df = pd.read_csv("50_restaurant1.csv")

# Ensure correct column
if "cleaned_review" not in df.columns:
    raise ValueError("❌ CSV must contain a 'cleaned_review' column")

# -------------------------------
# 2. Aggregate reviews per restaurant
# -------------------------------
grouped = df.groupby("restaurant")["cleaned_review"].apply(lambda x: " ".join(x)).reset_index()

# -------------------------------
# 3. Train TF-IDF model
# -------------------------------
vectorizer = TfidfVectorizer(stop_words="english", max_features=5000)
tfidf_matrix = vectorizer.fit_transform(grouped["cleaned_review"])

# -------------------------------
# 4. Compute similarity matrix
# -------------------------------
similarity = cosine_similarity(tfidf_matrix)

# -------------------------------
# 5. Save everything
# -------------------------------
joblib.dump(vectorizer, "tfidf_restaurant.pkl")
joblib.dump(grouped, "restaurants_grouped.pkl")       # restaurant → reviews mapping
joblib.dump(similarity, "restaurant_similarity.pkl")  # similarity matrix

print("✅ TF-IDF recommender model trained and saved!")
