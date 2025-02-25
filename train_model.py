import numpy as np
import pickle
from sklearn.linear_model import LogisticRegression

# Sample training data
# Features: [temperature, humidity, NDVI]
# Label: 1 for High Risk, 0 for Low/Moderate Risk
# These are synthetic examples:
X = np.array([
    [38, 35, 0.2],   # High risk: high temp, low humidity, low NDVI
    [36, 40, 0.3],   # High risk: borderline high risk
    [34, 50, 0.6],   # Low risk: moderate temp, high humidity, high NDVI
    [32, 60, 0.7],   # Low risk
    [40, 30, 0.25],  # High risk
    [29, 55, 0.8],   # Low risk
    [41, 28, 0.2],   # High risk
    [33, 65, 0.75],  # Low risk
    [35, 45, 0.5],   # Borderline low risk
    [39, 33, 0.35],  # High risk
    [30, 70, 0.9],   # Low risk
    [37, 42, 0.4],   # Borderline; consider high risk
    [42, 32, 0.2],   # High risk
    [31, 60, 0.85],  # Low risk
    [36, 38, 0.3],   # High risk
])

# Labels corresponding to the data above
y = np.array([1, 1, 0, 0, 1, 0, 1, 0, 0, 1, 0, 1, 1, 0, 1])

# Train a logistic regression model
model = LogisticRegression()
model.fit(X, y)

# Optionally, print model performance on training data (for debugging)
print("Training accuracy:", model.score(X, y))

# Save the trained model to a file
with open("risk_model.pkl", "wb") as f:
    pickle.dump(model, f)

print("Model trained and saved as risk_model.pkl!")
