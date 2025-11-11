import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
import joblib
from svm_scratch import LinearSVM


df = pd.read_csv("50_restaurant1.csv")


df["sentiment"] = df["rating"].apply(lambda r: 1 if r >= 3 else 0)  # 1=Positive, 0=Negative


tfidf = TfidfVectorizer(max_features=5000, ngram_range=(1,2))
X = tfidf.fit_transform(df["cleaned_review"]).toarray()  # already cleaned
y = df["sentiment"].values


svm = LinearSVM(lr=0.001, epochs=5000, batch_size=64)
svm.fit(X, y)


joblib.dump({"w": svm.w, "b": svm.b}, "svm_model_scratch.pkl")
joblib.dump(tfidf, "tfidf_vectorizer.pkl")

print("SVM model and vectorizer saved successfully!")
