import numpy as np
import pandas as pd
import re
from nltk.corpus import stopwords
from nltk.stem import PorterStemmer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import StandardScaler


data = pd.read_csv("train1.csv")  

data['label'] = data['rating'].apply(lambda x: 1 if x >= 3 else 0)

X_texts = data['cleaned_review'].values
y = data['label'].values


stop_words = set(stopwords.words("english"))
stemmer = PorterStemmer()

def preprocess(text):
    text = text.lower()
    text = re.sub(r'[^a-z\s]', '', text)  # keep only letters
    tokens = [stemmer.stem(w) for w in text.split() if w not in stop_words]
    return " ".join(tokens)

X_texts = [preprocess(t) for t in X_texts]


vectorizer = TfidfVectorizer(max_features=2000)
X = vectorizer.fit_transform(X_texts).toarray()

# Normalize
scaler = StandardScaler()
X = scaler.fit_transform(X)


class LinearSVM:
    def __init__(self, lr=0.001, lambda_param=0.01, n_iters=1000):
        self.lr = lr
        self.lambda_param = lambda_param
        self.n_iters = n_iters
        self.w = None
        self.b = None

    def fit(self, X, y):
        n_samples, n_features = X.shape
        y_ = np.where(y <= 0, -1, 1)  # convert 0->-1, 1->1

        self.w = np.zeros(n_features)
        self.b = 0

        for _ in range(self.n_iters):
            for idx, x_i in enumerate(X):
                condition = y_[idx] * (np.dot(x_i, self.w) - self.b) >= 1
                if condition:
                    self.w -= self.lr * (2 * self.lambda_param * self.w)
                else:
                    self.w -= self.lr * (2 * self.lambda_param * self.w - np.dot(x_i, y_[idx]))
                    self.b -= self.lr * y_[idx]

    def predict(self, X):
        approx = np.dot(X, self.w) - self.b
        return np.sign(approx)


print("Training SVM model...")
svm = LinearSVM(lr=0.001, lambda_param=0.01, n_iters=1000)
svm.fit(X, y)
print("Training completed!")


try:
    test_data = pd.read_csv("cleaned_reviews1.csv")  # column: Review
    test_reviews = [preprocess(t) for t in test_data['Review'].values]
    X_test = vectorizer.transform(test_reviews).toarray()
    X_test = scaler.transform(X_test)

    preds = svm.predict(X_test)
    preds = np.where(preds == -1, 0, 1)  # convert back to 0/1
    labels = ["Negative" if p == 0 else "Positive" for p in preds]

    test_data['Sentiment'] = labels
    print("\nCSV Test Results:")
    print(test_data)

    test_data.to_csv("results.csv", index=False)
    print("Results saved to results.csv")
except Exception as e:
    print("\nNo test.csv found. Skipping CSV test.")


def predict_single_review(review_text):
    review = preprocess(review_text)
    x_vec = vectorizer.transform([review]).toarray()
    x_vec = scaler.transform(x_vec)
    pred = svm.predict(x_vec)[0]
    sentiment = "Positive" if pred == 1 else "Negative"
    return sentiment


while True:
    review_input = input("\nEnter a review (or type 'exit' to quit): ")
    if review_input.lower() == "exit":
        print("Goodbye!")
        break
    sentiment = predict_single_review(review_input)
    print("Predicted Sentiment:", sentiment)
