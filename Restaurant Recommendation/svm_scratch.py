import numpy as np

class LinearSVM:
    def __init__(self, lr=0.001, epochs=5000, C=1.0, batch_size=64):
        self.lr = lr
        self.epochs = epochs
        self.C = C
        self.batch_size = batch_size
        self.w = None
        self.b = None

    def fit(self, X, y):
        n_samples, n_features = X.shape
        y_ = np.where(y <= 0, -1, 1)  # convert 0->-1, 1->1

        self.w = np.zeros(n_features)
        self.b = 0

        for _ in range(self.epochs):
            indices = np.random.permutation(n_samples)
            X_shuffled = X[indices]
            y_shuffled = y_[indices]

            for start in range(0, n_samples, self.batch_size):
                end = start + self.batch_size
                xb = X_shuffled[start:end]
                yb = y_shuffled[start:end]

                condition = yb * (xb @ self.w + self.b) >= 1
                dw = 2*(1/self.epochs)*self.w - np.dot(xb[~condition].T, yb[~condition])/max(1, xb[~condition].shape[0])
                db = -np.sum(yb[~condition])/max(1, xb[~condition].shape[0])

                self.w -= self.lr * dw
                self.b -= self.lr * db

    def predict(self, X):
        approx = X @ self.w + self.b
        return np.where(approx >= 0, 1, 0)
