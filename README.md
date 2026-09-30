# Digital Climate Advisory System for Agriculture

This project implements an intelligent agricultural decision support system using Deep Learning (LSTM) and a Rule-Based Advisory Engine.

## 📂 Folder Structure

```
dacs project/
│
├── farmer_advisory_dataset_final.csv  # The main agricultural dataset
├── app.py                             # Main Flask Application API and UI
├── requirements.txt                   # Python dependencies
│
├── src/                               # Source code directory
│   ├── model_training.py              # Script to build, train, and save the LSTM model
│   └── advisory_engine.py             # Rule-based logic for agricultural advisory
│
└── models/                            # Saved models and scalers (generated after training)
    ├── weather_lstm_model.h5
    └── scaler.pkl
```

## ⚙️ Explanation of Workflow

### 1. Data Processing & Time-Series Modeling (`src/model_training.py`)
- **Data Loading:** Reads the `farmer_advisory_dataset_final.csv` dataset.
- **Feature Selection:** Extracts critical weather features: `avg_temp_c`, `total_rainfall_mm`, and `avg_humidity_percent`.
- **Normalization:** Scales the values using `MinMaxScaler` so the Neural Network can learn effectively.
- **Sequence Creation:** Transforms the data into sliding windows (sequences) of 10 time-steps. For every 10 sequential weather observations, the model tries to predict the 11th.
- **LSTM Network:** A deep network utilizing Long Short-Term Memory (LSTM) layers ideal for sequence data. It predicts continuous future values for Temp, Rainfall, and Humidity.
- **Output:** Saves the trained `weather_lstm_model.h5` and the `scaler.pkl` to the `models/` directory for production inference.

### 2. Intelligent Advisory Engine (`src/advisory_engine.py`)
This module takes the raw numbers predicted by the LSTM model and translates them into human-readable action items:
- **Irrigation Advisory:** Balances predicted rainfall, humidity, and temperature. For example, if heavy rainfall is predicted (>200mm), it advises holding off on irrigation. If it's hot and dry, it advises immediate irrigation.
- **Crop Health Advisory:** Monitors extreme temperatures. Triggers warnings for heat stress (>35°C) and severe risk (>40°C), advising farmers to take protective measures like shading.
- **Extreme Weather Alerts:** Monitors both severe floods (high rainfall) and droughts (low rainfall combined with high heat) and issues high-priority alerts to the farmer.

### 3. Flask Web Application (`app.py`)
- Acts as the frontend dashboard and API server.
- **Contextual View:** Provides endpoints for historical metadata and benchmarks.
- **Forecasting:** Uses live Open-Meteo API data and historical benchmarks, feeding into the LSTM model to predict Temp, Rainfall, and Humidity.
- **Advisory Output:** Feeds predictions into the Advisory Engine and serves the results to a modern web interface.

## 🚀 How to Run the System

1. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Train the LSTM Model:**
   First, you must train the model and generate the scaler using the provided dataset.
   ```bash
   python src/model_training.py
   ```
   *(This will create the `models/` folder containing your trained artifacts.)*

3. **Launch the Application:**
   ```bash
   python app.py
   ```
   This will start a local server. Open `http://127.0.0.1:5000` in your web browser to view the application.
