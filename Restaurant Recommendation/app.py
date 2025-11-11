from flask import Flask, jsonify, render_template, request
import pandas as pd
import joblib
import numpy as np

app = Flask(__name__)

# ============================================================
# Load Review Data
# ============================================================
DF = pd.read_csv("50_restaurant1.csv")
DF.columns = [c.strip().lower() for c in DF.columns]
DF.rename(columns={"restaurant_name": "restaurant"}, inplace=True)
DF["rating"] = pd.to_numeric(DF["rating"], errors="coerce").fillna(0).astype(int)
DF["sentiment"] = DF["rating"].apply(lambda r: "Positive" if r >= 3 else "Negative")

# ============================================================
# Load Restaurant Details
# ============================================================
DETAILS = pd.read_csv("restaurant_list.csv")
DETAILS.columns = [c.strip().lower() for c in DETAILS.columns]
DETAILS.rename(columns={"name": "restaurant"}, inplace=True)

# ============================================================
# Load Sentiment Model
# ============================================================
tfidf_vectorizer = joblib.load("tfidf_vectorizer.pkl")
model_data = joblib.load("svm_model_scratch.pkl")
w, b = model_data["w"], model_data["b"]

def predict_scratch(X):
    approx = X @ w + b
    return np.where(approx >= 0, 1, 0)

# ============================================================
# Load TF-IDF CBF Model
# ============================================================
try:
    restaurant_vectorizer = joblib.load("tfidf_restaurant.pkl")
    grouped_restaurants = joblib.load("restaurants_grouped.pkl")
    restaurant_similarity = joblib.load("restaurant_similarity.pkl")
    print("✅ Loaded TF-IDF similarity model for recommendations.")
except:
    restaurant_vectorizer = None
    grouped_restaurants = None
    restaurant_similarity = None
    print("⚠️ Could not load TF-IDF similarity model files.")

# ============================================================
# Core CBF Recommender
# ============================================================
def recommend_similar_restaurants(restaurant, top_n=5):
    """CBF: Recommend similar restaurants using TF-IDF similarity."""
    if grouped_restaurants is None or restaurant_similarity is None:
        return []

    restaurant_lower = restaurant.strip().lower()
    matches = grouped_restaurants[grouped_restaurants["restaurant"].str.lower() == restaurant_lower]
    if matches.empty:
        return []

    idx = matches.index[0]
    sim_scores = list(enumerate(restaurant_similarity[idx]))
    sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)
    top_indices = [i for i, _ in sim_scores[1:top_n + 1]]
    return grouped_restaurants.iloc[top_indices]["restaurant"].tolist()

# ============================================================
# Summarize Restaurant
# ============================================================
def summarize_for(name: str):
    name = (name or "").strip().lower()
    if not name:
        return None

    sub = DF[DF["restaurant"].str.lower().str.contains(name)]
    if sub.empty:
        return None

    total = len(sub)
    avg_rating = round(float(sub["rating"].mean()), 2)
    rating_counts = {str(i): int((sub["rating"] == i).sum()) for i in range(1, 6)}
    pos = int((sub["sentiment"] == "Positive").sum())
    neg = int((sub["sentiment"] == "Negative").sum())
    examples_pos = sub[sub["sentiment"] == "Positive"]["cleaned_review"].head(3).tolist()
    examples_neg = sub[sub["sentiment"] == "Negative"]["cleaned_review"].head(3).tolist()
    display_name = sub["restaurant"].value_counts().idxmax()

    details = DETAILS[DETAILS["restaurant"].str.lower() == display_name.lower()]
    location = details["location"].iloc[0] if not details.empty else None
    contact = details["contact number"].iloc[0] if not details.empty else None

    return {
        "restaurant": display_name,
        "total_reviews": total,
        "average_rating": avg_rating,
        "rating_counts": rating_counts,
        "positive": pos,
        "negative": neg,
        "examples": {"positive": examples_pos, "negative": examples_neg},
        "location": location,
        "contact": contact,
    }

# ============================================================
# ROUTES
# ============================================================
@app.route("/")
def home():
    return render_template("recommender.html")

@app.route("/dashboard")
def dashboard():
    return render_template("index.html")

@app.route("/api/restaurants")
def restaurants():
    return jsonify(sorted(DF["restaurant"].dropna().unique().tolist()))

@app.route("/api/restaurants_with_details")
def restaurants_with_details():
    merged = DETAILS.dropna(subset=["location", "contact number"])
    data = [
        {"restaurant": d["restaurant"], "location": d["location"], "contact": d["contact number"]}
        for _, d in merged.iterrows()
    ]
    return jsonify(data)

@app.route("/api/summary")
def summary():
    name = request.args.get("restaurant", "")
    result = summarize_for(name)
    if result is None:
        return jsonify({"error": "Restaurant not found"}), 404
    return jsonify(result)

# ============================================================
# Similar Restaurants (Enhanced CBF + Fallback)
# ============================================================
@app.route("/api/similar_restaurants")
def similar_restaurants():
    name = request.args.get("restaurant", "").strip()
    if not name:
        return jsonify([])

    try:
        recs = recommend_similar_restaurants(name, top_n=5)

        if not recs:
            # fallback: similar name or location
            print(f"⚠️ No CBF results for '{name}', using fallback...")
            first_word = name.split()[0]
            partial = DETAILS[
                DETAILS["restaurant"].str.contains(first_word, case=False, na=False)
            ]["restaurant"].tolist()
            location = DETAILS.loc[
                DETAILS["restaurant"].str.lower() == name.lower(), "location"
            ]
            if not location.empty:
                loc = location.iloc[0]
                loc_based = DETAILS[
                    DETAILS["location"].str.lower() == str(loc).lower()
                ]["restaurant"].tolist()
                recs = list(set(partial + loc_based))[:5]
            else:
                recs = partial[:5]

        merged = DETAILS[DETAILS["restaurant"].isin(recs)][
            ["restaurant", "location", "contact number"]
        ]
        avg_ratings = DF.groupby("restaurant")["rating"].mean().round(2)
        merged["average_rating"] = merged["restaurant"].map(avg_ratings).fillna(0)

        formatted = [
            {
                "restaurant": row["restaurant"],
                "location": row.get("location", "N/A"),
                "contact": row.get("contact number", "N/A"),
                "average_rating": row.get("average_rating", 0.0)
            }
            for _, row in merged.iterrows()
        ]
        return jsonify(formatted)
    except Exception as e:
        print(f"⚠️ Error generating similar restaurants for '{name}': {e}")
        return jsonify([])

# ============================================================
# Hybrid CBF + Rating-based Location Recommender
# ============================================================
@app.route("/api/recommend_by_location")
def recommend_by_location():
    location = request.args.get("location", "").strip().lower()
    if not location:
        return jsonify([])

    sub = DETAILS[DETAILS["location"].str.lower().str.contains(location, na=False)]
    if sub.empty:
        return jsonify([])

    if grouped_restaurants is not None and restaurant_similarity is not None:
        all_restos = grouped_restaurants["restaurant"].tolist()
        scores = []
        for r in sub["restaurant"]:
            if r in all_restos:
                idx = all_restos.index(r)
                sim_score = restaurant_similarity[idx].mean()
                scores.append((r, sim_score))
        sim_df = pd.DataFrame(scores, columns=["restaurant", "cbf_score"])
    else:
        sim_df = pd.DataFrame({"restaurant": sub["restaurant"], "cbf_score": 0.5})

    ratings = DF.groupby("restaurant")["rating"].mean().reset_index()
    ratings.rename(columns={"rating": "average_rating"}, inplace=True)

    merged = sub.merge(ratings, on="restaurant", how="left").merge(sim_df, on="restaurant", how="left")
    merged["hybrid_score"] = 0.7 * merged["average_rating"].fillna(3) + 0.3 * merged["cbf_score"].fillna(0.5)
    merged = merged.sort_values("hybrid_score", ascending=False)

    formatted = [
        {
            "restaurant": row["restaurant"],
            "location": row["location"],
            "contact": row.get("contact number", "N/A"),
            "average_rating": round(row["average_rating"], 2) if pd.notna(row["average_rating"]) else 0.0
        }
        for _, row in merged.iterrows()
    ]
    return jsonify(formatted)

# ============================================================
# Top Restaurants (Hybrid Global Recommender)
# ============================================================
@app.route("/api/recommendations")
def recommendations():
    try:
        if restaurant_similarity is None or grouped_restaurants is None:
            grouped = DF.groupby("restaurant")["rating"].mean().reset_index()
            top = grouped.sort_values("rating", ascending=False).head(6)["restaurant"].tolist()
        else:
            avg_sims = restaurant_similarity.mean(axis=1)
            ratings = (
                DF.groupby("restaurant")["rating"]
                .mean()
                .reindex(grouped_restaurants["restaurant"])
                .fillna(3)
            )
            hybrid_score = 0.7 * ratings.values + 0.3 * avg_sims
            top_indices = hybrid_score.argsort()[::-1][:6]
            top = grouped_restaurants.iloc[top_indices]["restaurant"].tolist()

        recs = DETAILS[DETAILS["restaurant"].isin(top)][["restaurant", "location", "contact number"]]
        formatted = [
            {
                "restaurant": row["restaurant"],
                "location": row.get("location", "N/A"),
                "contact": row.get("contact number", "N/A")
            }
            for _, row in recs.iterrows()
        ]
        return jsonify(formatted)
    except Exception as e:
        print("⚠️ Error in recommendations:", e)
        return jsonify([])

# ============================================================
# Feedback + User Recommendations (same as before)
# ============================================================
@app.route("/api/submit_feedback", methods=["POST"])
def submit_feedback():
    data = request.json
    restaurant = data.get("restaurant", "").strip()
    review = data.get("review", "").strip()
    rating = data.get("rating", None)

    if not restaurant:
        return jsonify({"error": "Missing restaurant"}), 400

    if review:
        X = tfidf_vectorizer.transform([review]).toarray()
        pred = predict_scratch(X)[0]
        sentiment = "Positive" if pred == 1 else "Negative"
        rating = int(rating) if rating else (4 if sentiment == "Positive" else 2)
    elif rating is not None:
        rating = int(rating)
        if rating not in [1, 2, 3, 4, 5]:
            return jsonify({"error": "Invalid rating"}), 400
        sentiment = "Positive" if rating >= 3 else "Negative"
        review = f"User submitted rating {rating}"
    else:
        return jsonify({"error": "Missing review or rating"}), 400

    global DF
    DF = pd.concat([DF, pd.DataFrame([{
        "restaurant": restaurant,
        "rating": rating,
        "sentiment": sentiment,
        "cleaned_review": review
    }])], ignore_index=True)
    DF.to_csv("50_restaurant1.csv", index=False)

    return jsonify({"restaurant": restaurant, "sentiment": sentiment, "rating": rating})

# ============================================================
# Run
# ============================================================
if __name__ == "__main__":
    app.run(debug=True)
