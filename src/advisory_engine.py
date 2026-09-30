def generate_advisory(temp, rainfall, humidity, crop=None, season=None, benchmark=None):
    """
    Generates human-readable agricultural advice based on predicted weather conditions
    and compares them to historical benchmarks for specific crops.
    """
    
    advisories = {
        "summary": "Conditions are broadly favourable. Standard agronomic practices should suffice.",
        "risk_assessment": "Low risk. No immediate threats detected.",
        "irrigation_management": "Maintain standard irrigation schedule.",
        "soil_nutrient": "Standard soil management recommended.",
        "resilience_actions": [
            "Monitor local weather reports daily.",
            "Maintain standard fertilization schedule.",
            "Ensure proper drainage in fields."
        ],
        "dataset_irrigation": "Standard irrigation guidance.",
        "crop_specific": "",
        "resilience_score": 100,
        "breakdown": {
            "temp_fit": 100,
            "rain_fit": 100,
            "hum_fit": 100,
            "soil_fit": 100,
            "nutrient_fit": 100
        },
        "live_alert": "Conditions are stable. No immediate real-time threats detected."
    }
    
    if not benchmark:
        # Default simple logic if no benchmark is provided
        resilience = 80
        if temp > 35 or temp < 10: 
            resilience -= 20
            advisories["live_alert"] = "Caution: Temperature outside optimal growth range."
        if rainfall < 10: 
            resilience -= 15
            advisories["live_alert"] = "Alert: Low rainfall detected."
        advisories["resilience_score"] = resilience
        return advisories

    # 1. Resilience Score Calculation
    temp_diff = abs(temp - benchmark['avg_temp'])
    rain_diff = abs(rainfall - benchmark['avg_rain'])
    hum_diff = abs(humidity - benchmark['avg_hum'])
    
    # Penalties (max 100)
    temp_fit = max(0, 100 - (temp_diff * 5))
    rain_fit = max(0, 100 - (rain_diff * 0.3))
    hum_fit = max(0, 100 - (hum_diff * 3))
    soil_fit = 90 if benchmark['soil_type'] != "Unknown" else 50
    nutrient_fit = min(100, int(benchmark.get('nitrogen_index', 50) + benchmark.get('carbon_index', 50)) // 2)

    advisories["breakdown"] = {
        "temp_fit": int(temp_fit),
        "rain_fit": int(rain_fit),
        "hum_fit": int(hum_fit),
        "soil_fit": int(soil_fit),
        "nutrient_fit": int(nutrient_fit)
    }
    
    score = (temp_fit * 0.3) + (rain_fit * 0.3) + (hum_fit * 0.1) + (soil_fit * 0.15) + (nutrient_fit * 0.15)
    advisories["resilience_score"] = int(score)

    # 2. Live Alerts (Real-time checks)
    if temp > benchmark['avg_temp'] + 4:
        advisories["live_alert"] = f"⚠️ Heat Stress Alert: Temperature is {round(temp_diff, 1)}°C above average. High evaporation risk."
    elif temp < benchmark['avg_temp'] - 4:
        advisories["live_alert"] = f"❄️ Cold Warning: Temperature is {round(temp_diff, 1)}°C below average. Growth may slow."
    elif rainfall > benchmark['avg_rain'] * 1.4:
        advisories["live_alert"] = "🌧️ Flash Flood Risk: Excessive rainfall detected relative to historical norms."
    elif rainfall < benchmark['avg_rain'] * 0.3 and benchmark['avg_rain'] > 50:
        advisories["live_alert"] = "🏜️ Drought Warning: Significant moisture deficit detected. Immediate irrigation needed."
    else:
        advisories["live_alert"] = "✅ Stable Growth Conditions: Climate variables are within optimal historical ranges."

    # 3. Summary
    state_str = f"{benchmark.get('state', '')} · " if benchmark and benchmark.get('state') else ""
    real_time_prefix = "📡 Real-time Assessment: "
    if score > 80:
        advisories["summary"] = f"{real_time_prefix}{crop} · {state_str}{season} — Conditions are optimal for high yield performance."
    elif score > 60:
        advisories["summary"] = f"{real_time_prefix}{crop} · {state_str}{season} — Conditions are broadly favourable. Standard practices suffice."
    else:
        advisories["summary"] = f"{real_time_prefix}{crop} · {state_str}{season} — Sub-optimal conditions. Targeted interventions required."

    # 4. Risk Assessment
    risks = []
    if temp > benchmark['avg_temp'] + 5:
        risks.append(f"Temperature {temp}°C is significantly higher than {benchmark['avg_temp']}°C — thermal stress likely.")
    elif temp < benchmark['avg_temp'] - 5:
        risks.append(f"Cooler than average ({temp}°C vs {benchmark['avg_temp']}°C) may delay maturation.")
        
    if rainfall < benchmark['avg_rain'] * 0.5:
        risks.append(f"Rainfall {rainfall}mm is {round((1 - rainfall/benchmark['avg_rain'])*100)}% below levels — drought risk.")
    elif rainfall > benchmark['avg_rain'] * 1.5:
        risks.append(f"Excessive rainfall ({rainfall}mm vs {benchmark['avg_rain']}mm) — risk of waterlogging.")
        
    if risks:
        advisories["risk_assessment"] = " ".join(risks)
    else:
        advisories["risk_assessment"] = "Climate variables are within stable ranges. Risk of environmental stress is low."

    # 5. Irrigation & Water Management
    if rainfall < benchmark['avg_rain'] * 0.7:
        advisories["irrigation_management"] = f"Deficit: {round(benchmark['avg_rain'] - rainfall)}mm. Monitor soil moisture weekly and apply supplemental irrigation. Prefer drip irrigation to conserve water."
    elif rainfall > benchmark['avg_rain'] * 1.3:
        advisories["irrigation_management"] = "Surplus detected. Ensure drainage channels are clear. Suspend scheduled irrigation to avoid root rot."
    else:
        advisories["irrigation_management"] = "Optimal moisture. Continue with baseline irrigation schedule as per crop requirements."

    # 6. Soil & Nutrient Guidance
    soil_type = benchmark.get('soil_type', 'Mixed')
    nitro = benchmark.get('nitrogen_index', 50)
    carb = benchmark.get('carbon_index', 50)
    nitro_status = "low" if nitro < 40 else "moderate" if nitro < 70 else "high"
    carb_status = "adequate" if carb > 50 else "low"
    advisories["soil_nutrient"] = f"{soil_type} soil base. Nitrogen availability is {nitro_status} ({round(nitro)}/100). Carbon availability is {carb_status} ({round(carb)}/100). Apply balanced N-P-K fertilizer to compensate for any deficit."

    # 7. Input & Resource Management
    fert = round(benchmark.get('fertilizer', 0), 1)
    pest = round(benchmark.get('pesticide', 0), 1)
    prod = round(benchmark.get('production', 0), 1)
    area = round(benchmark.get('area', 0), 1)
    advisories["input_guidance"] = f"Typical resource needs for {crop}: Fertilizer ~{fert} units, Pesticide ~{pest} units. Expected yield based on historical {area}ha area is ~{prod} units."

    # 8. Resilience Actions
    advisories["resilience_actions"] = [
        f"Calibrate fertilizer application to {fert} units based on {crop} history.",
        f"Monitor for humidity-driven pests (current hum: {humidity}%).",
        f"Maintain soil moisture at {round(benchmark['avg_hum'])}% level if possible.",
        "Consider intercropping to mitigate climate-related yield loss."
    ]

    # 9. Dataset Irrigation Guidance
    advisories["dataset_irrigation"] = benchmark.get('dataset_irrigation_advice', f"Standard irrigation for {crop}")

    return advisories

if __name__ == "__main__":
    # Test the logic
    print("Testing Advisory Engine...")
    print(generate_advisory(temp=41, rainfall=10, humidity=30, crop="Wheat", season="Rabi", benchmark={'avg_temp': 25, 'avg_rain': 100, 'avg_hum': 60, 'soil_type': 'Loamy', 'nitrogen_index': 50, 'carbon_index': 50}))

