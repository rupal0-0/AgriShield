import os
import pandas as pd
import numpy as np
import tensorflow as tf
import joblib
import requests
from flask import Flask, render_template, request, jsonify
from src.advisory_engine import generate_advisory

app = Flask(__name__)

# Try to load models and data
DATA_PATH = 'farmer_advisory_dataset_final.csv'
MODEL_PATH = 'models/weather_lstm_model.h5'
SCALER_PATH = 'models/scaler.pkl'

df = None
model = None
scaler = None
global_averages = {}

def load_assets():
    global df, model, scaler, global_averages
    try:
        # Load main dataset
        df_csv = pd.read_csv(DATA_PATH)
        
        # Load new AgriShield records if available
        AGRI_JSON_PATH = 'data/agrishield_records.json'
        if os.path.exists(AGRI_JSON_PATH):
            import json
            with open(AGRI_JSON_PATH, 'r', encoding='utf-8') as f:
                records = json.load(f)
            df_json = pd.DataFrame(records)
            
            # Map JSON columns to CSV columns
            mapping = {
                'avg_temp': 'avg_temp_c',
                'avg_rainfall': 'total_rainfall_mm',
                'avg_humidity': 'avg_humidity_percent',
                'avg_yield': 'yield',
                'avg_area': 'area',
                'avg_production': 'production',
                'avg_fertilizer': 'fertilizer',
                'avg_pesticide': 'pesticide',
                'avg_co2': 'CO2_ppm',
                'avg_o2': 'O2_percent',
                'avg_n2': 'N2_percent',
                'avg_h2o': 'H2O_vapor_percent',
                'avg_n_avail': 'Nitrogen_availability_index',
                'avg_c_avail': 'Carbon_availability_index',
                'avg_o_avail': 'Oxygen_availability_index',
                'irrigation': 'irrigation_advisory'
            }
            df_json = df_json.rename(columns=mapping)
            
            # Merge datasets
            df = pd.concat([df_csv, df_json], ignore_index=True)
            print(f"Loaded {len(df_csv)} CSV records and {len(df_json)} JSON records.")
        else:
            df = df_csv
            print(f"Loaded {len(df)} CSV records.")

        # Clean strings
        for col in ['state', 'crop', 'season']:
            if col in df.columns:
                df[col] = df[col].astype(str).str.strip()
        
        df = df.fillna(method='ffill').fillna(method='bfill')
        
        # Pre-calculate global averages for fallback
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        global_averages = df[numeric_cols].mean().to_dict()
        global_averages['soil_type'] = df['soil_type'].mode().iloc[0] if 'soil_type' in df.columns else "Mixed"
        global_averages['irrigation_advisory'] = df['irrigation_advisory'].mode().iloc[0] if 'irrigation_advisory' in df.columns else "Standard irrigation."
    except Exception as e:
        print(f"Error loading data: {e}")
        df = pd.DataFrame(columns=['state', 'crop', 'season', 'avg_temp_c', 'total_rainfall_mm', 'avg_humidity_percent', 'yield', 'soil_type'])

        
    try:
        model = tf.keras.models.load_model(MODEL_PATH, compile=False)
        scaler = joblib.load(SCALER_PATH)
    except Exception as e:
        print(f"Error loading model/scaler: {e}")

load_assets()

def get_lstm_prediction(lat, lon):
    global model, scaler
    if model is None or scaler is None:
        return None
        
    try:
        # Fetch past 10 days of weather to feed the LSTM
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&past_days=10&daily=temperature_2m_mean,precipitation_sum,relative_humidity_2m_mean&timezone=auto"
        response = requests.get(url).json()
        
        temps = response['daily']['temperature_2m_mean']
        rains = response['daily']['precipitation_sum']
        hums = response['daily']['relative_humidity_2m_mean']
        
        # Prepare input (10 steps, 3 features)
        X = np.array([temps, rains, hums]).T # (10, 3)
        X_scaled = scaler.transform(X)
        X_reshaped = X_scaled.reshape(1, 10, 3)
        
        pred_scaled = model.predict(X_reshaped)
        # Assuming the model predicts 1 step (current/next day)
        # We unscale only the features part
        pred = scaler.inverse_transform(pred_scaled)[0]
        
        return {
            "temperature": float(pred[0]),
            "rainfall": float(pred[1]),
            "humidity": float(pred[2])
        }
    except Exception as e:
        print(f"LSTM Prediction failed: {e}")
        return None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/metadata')
def get_metadata():
    if df is None:
        return jsonify({"error": "Data not loaded"}), 500
    
    states = sorted(df['state'].unique().tolist())
    crops = sorted(df['crop'].unique().tolist())
    seasons = sorted(df['season'].unique().tolist())
    
    return jsonify({
        "states": states,
        "crops": crops,
        "seasons": seasons,
        "total_records": len(df)
    })

@app.route('/api/benchmark', methods=['POST'])
def get_benchmark():
    data = request.json
    state = data.get('state')
    crop = data.get('crop')
    season = data.get('season')
    
    filtered_df = df.copy()
    if state: filtered_df = filtered_df[filtered_df['state'] == state]
    if crop: filtered_df = filtered_df[filtered_df['crop'] == crop]
    if season: filtered_df = filtered_df[filtered_df['season'] == season]
    
    if not filtered_df.empty:
        benchmark = {
            "state": state or "Unknown",
            "avg_temp": round(filtered_df['avg_temp_c'].mean(), 2),
            "avg_rain": round(filtered_df['total_rainfall_mm'].mean(), 2),
            "avg_hum": round(filtered_df['avg_humidity_percent'].mean(), 2),
            "avg_yield": round(filtered_df['yield'].mean(), 2),
            "soil_type": filtered_df['soil_type'].mode().iloc[0] if not filtered_df['soil_type'].empty else "Mixed",
            "nitrogen_index": round(filtered_df['Nitrogen_availability_index'].mean(), 2),
            "carbon_index": round(filtered_df['Carbon_availability_index'].mean(), 2),
            "oxygen_index": round(filtered_df['Oxygen_availability_index'].mean(), 2),
            "co2_ppm": round(filtered_df['CO2_ppm'].mean(), 1),
            "pesticide": round(filtered_df['pesticide'].mean(), 2) if 'pesticide' in filtered_df.columns else 0,
            "fertilizer": round(filtered_df['fertilizer'].mean(), 2) if 'fertilizer' in filtered_df.columns else 0,
            "production": round(filtered_df['production'].mean(), 2) if 'production' in filtered_df.columns else 0,
            "area": round(filtered_df['area'].mean(), 2) if 'area' in filtered_df.columns else 0,
            "h2o_vapor": round(filtered_df['H2O_vapor_percent'].mean(), 2) if 'H2O_vapor_percent' in filtered_df.columns else 0,
            "n2_percent": round(filtered_df['N2_percent'].mean(), 2) if 'N2_percent' in filtered_df.columns else 0,
            "o2_percent": round(filtered_df['O2_percent'].mean(), 2) if 'O2_percent' in filtered_df.columns else 0,
            "dataset_irrigation_advice": filtered_df['irrigation_advisory'].mode().iloc[0] if 'irrigation_advisory' in filtered_df.columns and not filtered_df['irrigation_advisory'].empty else "Standard irrigation."
        }
    else:
        benchmark = {
            "state": state or "Unknown",
            "avg_temp": round(global_averages.get('avg_temp_c', 25.0), 2),
            "avg_rain": round(global_averages.get('total_rainfall_mm', 1000.0), 2),
            "avg_hum": round(global_averages.get('avg_humidity_percent', 60.0), 2),
            "avg_yield": round(global_averages.get('yield', 1.0), 2),
            "soil_type": global_averages.get('soil_type', "Mixed"),
            "nitrogen_index": round(global_averages.get('Nitrogen_availability_index', 50.0), 2),
            "carbon_index": round(global_averages.get('Carbon_availability_index', 50.0), 2),
            "oxygen_index": round(global_averages.get('Oxygen_availability_index', 50.0), 2),
            "co2_ppm": round(global_averages.get('CO2_ppm', 400.0), 1),
            "pesticide": round(global_averages.get('pesticide', 0), 2),
            "fertilizer": round(global_averages.get('fertilizer', 0), 2),
            "production": round(global_averages.get('production', 0), 2),
            "area": round(global_averages.get('area', 0), 2),
            "h2o_vapor": round(global_averages.get('H2O_vapor_percent', 0), 2),
            "n2_percent": round(global_averages.get('N2_percent', 0), 2),
            "o2_percent": round(global_averages.get('O2_percent', 0), 2),
            "dataset_irrigation_advice": global_averages.get('irrigation_advisory', "Standard irrigation.")
        }
    
    return jsonify(benchmark)

@app.route('/api/predict', methods=['POST'])
def predict():
    data = request.json
    state = data.get('state')
    crop = data.get('crop')
    season = data.get('season')
    
    # Check for manual overrides
    manual_temp = data.get('temp')
    manual_rain = data.get('rain')
    manual_hum = data.get('hum')
    
    if not state:
        return jsonify({"error": "State required"}), 400
        
    try:
        # Get historical benchmark
        filtered_df = df[(df['state'] == state) & (df['crop'] == crop) & (df['season'] == season)]
        if filtered_df.empty:
            filtered_df = df[(df['state'] == state) & (df['crop'] == crop)]
        if filtered_df.empty:
            filtered_df = df[df['crop'] == crop]
            
        if not filtered_df.empty:
            benchmark = {
                "state": state or "General",
                "avg_temp": round(filtered_df['avg_temp_c'].mean(), 2),
                "avg_rain": round(filtered_df['total_rainfall_mm'].mean(), 2),
                "avg_hum": round(filtered_df['avg_humidity_percent'].mean(), 2),
                "avg_yield": round(filtered_df['yield'].mean(), 2),
                "soil_type": filtered_df['soil_type'].mode().iloc[0] if not filtered_df['soil_type'].empty else "Mixed",
                "nitrogen_index": round(filtered_df['Nitrogen_availability_index'].mean(), 2),
                "carbon_index": round(filtered_df['Carbon_availability_index'].mean(), 2),
                "oxygen_index": round(filtered_df['Oxygen_availability_index'].mean(), 2),
                "co2_ppm": round(filtered_df['CO2_ppm'].mean(), 1),
                "pesticide": round(filtered_df['pesticide'].mean(), 2) if 'pesticide' in filtered_df.columns else 0,
                "fertilizer": round(filtered_df['fertilizer'].mean(), 2) if 'fertilizer' in filtered_df.columns else 0,
                "production": round(filtered_df['production'].mean(), 2) if 'production' in filtered_df.columns else 0,
                "area": round(filtered_df['area'].mean(), 2) if 'area' in filtered_df.columns else 0,
                "h2o_vapor": round(filtered_df['H2O_vapor_percent'].mean(), 2) if 'H2O_vapor_percent' in filtered_df.columns else 0,
                "n2_percent": round(filtered_df['N2_percent'].mean(), 2) if 'N2_percent' in filtered_df.columns else 0,
                "o2_percent": round(filtered_df['O2_percent'].mean(), 2) if 'O2_percent' in filtered_df.columns else 0,
                "dataset_irrigation_advice": filtered_df['irrigation_advisory'].mode().iloc[0] if 'irrigation_advisory' in filtered_df.columns and not filtered_df['irrigation_advisory'].empty else "Standard irrigation."
            }
        else:
            benchmark = {
                "state": state or "Unknown",
                "avg_temp": round(global_averages.get('avg_temp_c', 25.0), 2),
                "avg_rain": round(global_averages.get('total_rainfall_mm', 1000.0), 2),
                "avg_hum": round(global_averages.get('avg_humidity_percent', 60.0), 2),
                "avg_yield": round(global_averages.get('yield', 1.0), 2),
                "soil_type": global_averages.get('soil_type', "Mixed"),
                "nitrogen_index": round(global_averages.get('Nitrogen_availability_index', 50.0), 2),
                "carbon_index": round(global_averages.get('Carbon_availability_index', 50.0), 2),
                "oxygen_index": round(global_averages.get('Oxygen_availability_index', 50.0), 2),
                "co2_ppm": round(global_averages.get('CO2_ppm', 400.0), 1),
                "pesticide": round(global_averages.get('pesticide', 0), 2),
                "fertilizer": round(global_averages.get('fertilizer', 0), 2),
                "production": round(global_averages.get('production', 0), 2),
                "area": round(global_averages.get('area', 0), 2),
                "h2o_vapor": round(global_averages.get('H2O_vapor_percent', 0), 2),
                "n2_percent": round(global_averages.get('N2_percent', 0), 2),
                "o2_percent": round(global_averages.get('O2_percent', 0), 2),
                "dataset_irrigation_advice": global_averages.get('irrigation_advisory', "Standard irrigation.")
            }

        # Find alternatives
        alternatives = []
        if state:
            s_state = str(state).strip()
            s_season = str(season).strip() if season else ""
            s_crop = str(crop).strip() if crop else ""
            
            # Level 1: Same State + Same Season
            alt_df = df[(df['state'] == s_state) & (df['season'] == s_season) & (df['crop'] != s_crop)]
            
            # Level 2 Fallback: Same State, any season
            if alt_df.empty:
                alt_df = df[(df['state'] == s_state) & (df['crop'] != s_crop)]
                
            # Level 3: Global (avoid if possible, but better than nothing)
            if alt_df.empty:
                alt_df = df[df['crop'] != s_crop]

            if not alt_df.empty:
                alt_summary = alt_df.groupby('crop').agg({
                    'yield': 'mean',
                    'soil_type': lambda x: x.mode().iloc[0] if not x.mode().empty else "Mixed",
                    'total_rainfall_mm': 'mean'
                }).reset_index().sort_values(by='yield', ascending=False).head(5)
                
                for _, row in alt_summary.iterrows():
                    alternatives.append({
                        "crop": row['crop'],
                        "yield": round(float(row['yield']), 2),
                        "soil_type": row['soil_type'],
                        "rainfall": round(float(row['total_rainfall_mm']), 0),
                        "suitability": "High" if row['yield'] > (benchmark.get('avg_yield', 0) * 0.8) else "Medium"
                    })



        is_offline = False
        if manual_temp is not None:
            pred_temp, pred_rain, pred_hum = float(manual_temp), float(manual_rain), float(manual_hum)
        else:
            try:
                geo_res = requests.get(f"https://geocoding-api.open-meteo.com/v1/search?name={state}&count=1", timeout=5).json()
                lat, lon = geo_res['results'][0]['latitude'], geo_res['results'][0]['longitude']
                w_res = requests.get(f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m&daily=precipitation_sum", timeout=5).json()
                pred_temp, pred_rain, pred_hum = w_res['current']['temperature_2m'], w_res['daily']['precipitation_sum'][0], w_res['current']['relative_humidity_2m']
            except:
                pred_temp, pred_rain, pred_hum = benchmark['avg_temp'], benchmark['avg_rain'], benchmark['avg_hum']
                is_offline = True
        
        advisories = generate_advisory(pred_temp, pred_rain, pred_hum, crop, season, benchmark)
        
        # Calculate predicted yield based on resilience score and historical avg
        res_score = advisories.get("resilience_score", 100)
        hist_yield = benchmark.get("avg_yield", 0)
        # Simple heuristic: yield varies +/- 30% based on score
        predicted_yield = hist_yield * (0.7 + (res_score / 100) * 0.6)
        
        result = {
            "predictions": {
                "temperature": round(float(pred_temp), 1),
                "rainfall": round(float(pred_rain), 1),
                "humidity": round(float(pred_hum), 1),
                "yield": round(float(predicted_yield), 2)
            },
            "benchmark": benchmark,
            "advisories": advisories,
            "alternatives": alternatives,
            "state": state,
            "crop": crop,
            "season": season,
            "offline": is_offline,
            "live_alert": advisories.get("live_alert", "Stable conditions.")
        }
        
        print(f"Prediction for {state}/{crop}: Score {res_score}, Yield {predicted_yield}")

        # Final JSON-safe cleaning
        def clean(v):
            if isinstance(v, dict): return {k: clean(x) for k, x in v.items()}
            if isinstance(v, list): return [clean(x) for x in v]
            if isinstance(v, float) and (np.isnan(v) or np.isinf(v)): return 0.0
            return v
            
        return jsonify(clean(result))


    except Exception as e:
        print(f"Prediction Error: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
