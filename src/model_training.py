import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout
import joblib
import os

def create_sequences(data, seq_length):
    X = []
    y = []
    for i in range(len(data) - seq_length):
        X.append(data[i:i + seq_length])
        y.append(data[i + seq_length])
    return np.array(X), np.array(y)

def train_model(data_path, model_save_path, scaler_save_path, seq_length=10, epochs=10, batch_size=32):
    print("Loading data...")
    df = pd.read_csv(data_path)
    
    # Fill missing values if any
    df = df.fillna(method='ffill').fillna(method='bfill')
    
    # We will use temperature, rainfall, and humidity for forecasting
    features = ['avg_temp_c', 'total_rainfall_mm', 'avg_humidity_percent']
    
    # Ensure columns exist
    for f in features:
        if f not in df.columns:
            raise ValueError(f"Feature {f} not found in the dataset.")
            
    # Sort data by year and season if possible to make it somewhat sequential
    if 'year' in df.columns and 'season' in df.columns:
        df = df.sort_values(by=['year', 'season'])
    
    data = df[features].values
    
    print("Normalizing data...")
    scaler = MinMaxScaler()
    scaled_data = scaler.fit_transform(data)
    
    print("Creating sequences...")
    X, y = create_sequences(scaled_data, seq_length)
    
    # Split into train and test
    split = int(0.8 * len(X))
    X_train, X_test = X[:split], X[split:]
    y_train, y_test = y[:split], y[split:]
    
    print(f"Training shape: X={X_train.shape}, y={y_train.shape}")
    
    print("Building LSTM model...")
    model = Sequential([
        LSTM(64, return_sequences=True, input_shape=(seq_length, len(features))),
        Dropout(0.2),
        LSTM(32),
        Dropout(0.2),
        Dense(16, activation='relu'),
        Dense(len(features))
    ])
    
    model.compile(optimizer='adam', loss='mse', metrics=['mae'])
    
    print("Training model...")
    model.fit(
        X_train, y_train,
        epochs=epochs,
        batch_size=batch_size,
        validation_data=(X_test, y_test),
        verbose=1
    )
    
    print("Saving model and scaler...")
    # Create directories if they don't exist
    os.makedirs(os.path.dirname(model_save_path), exist_ok=True)
    os.makedirs(os.path.dirname(scaler_save_path), exist_ok=True)
    
    model.save(model_save_path)
    joblib.dump(scaler, scaler_save_path)
    print("Training complete!")

if __name__ == "__main__":
    DATA_PATH = "farmer_advisory_dataset_final.csv"
    MODEL_PATH = "models/weather_lstm_model.h5"
    SCALER_PATH = "models/scaler.pkl"
    
    # Using a small number of epochs for quick demonstration.
    # In production, this would be higher (e.g. 50-100)
    train_model(DATA_PATH, MODEL_PATH, SCALER_PATH, epochs=5)
