document.addEventListener('DOMContentLoaded', async () => {
    const stateSelect = document.getElementById('stateSelect');
    const cropSelect = document.getElementById('cropSelect');
    const seasonSelect = document.getElementById('seasonSelect');
    const generateBtn = document.getElementById('generateBtn');
    const loader = document.getElementById('loader');

    // Tab Switching Logic
    const tabBtns = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');
    
    function switchTab(targetId) {
        console.log("Switching to tab:", targetId);
        tabBtns.forEach(btn => {
            if (btn.getAttribute('data-tab') === targetId) {
                btn.classList.add('active');
            } else {
                btn.classList.remove('active');
            }
        });
        
        tabContents.forEach(content => {
            if (content.id === targetId) {
                content.classList.add('active');
                content.style.display = 'flex';
            } else {
                content.classList.remove('active');
                content.style.display = 'none';
            }
        });
    }

    tabBtns.forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.preventDefault();
            switchTab(btn.getAttribute('data-tab'));
        });
    });

    // Sliders
    const tempSlider = document.getElementById('tempSlider');
    const rainSlider = document.getElementById('rainSlider');
    const humSlider = document.getElementById('humSlider');
    const tempValDisp = document.getElementById('tempVal');
    const rainValDisp = document.getElementById('rainVal');
    const humValDisp = document.getElementById('humVal');

    // Score Circle
    const scoreCircle = document.getElementById('scoreCircle');

    // Breakdown Bars
    const breakdownBars = {
        temp: { val: document.getElementById('tempFitVal'), bar: document.getElementById('tempFitBar') },
        rain: { val: document.getElementById('rainFitVal'), bar: document.getElementById('rainFitBar') },
        hum: { val: document.getElementById('humFitVal'), bar: document.getElementById('humFitBar') },
        nutrient: { val: document.getElementById('nutrientFitVal'), bar: document.getElementById('nutrientFitBar') }
    };

    // Initialize Metadata
    try {
        const response = await fetch('/api/metadata');
        const data = await response.json();
        
        const populate = (select, list) => {
            if (list) {
                list.forEach(item => {
                    const opt = document.createElement('option');
                    opt.value = item;
                    opt.textContent = item;
                    select.appendChild(opt);
                });
            }
        };

        populate(stateSelect, data.states);
        populate(cropSelect, data.crops);
        populate(seasonSelect, data.seasons);

        setSafeText('statRecords', data.total_records.toLocaleString());
        setSafeText('statCrops', data.crops.length);
        setSafeText('statStates', data.states.length);
        setSafeText('recordCount', Math.floor(data.total_records / 500));

    } catch (err) {
        console.error("Error fetching metadata:", err);
    }

    // Slider Listeners
    tempSlider.addEventListener('input', (e) => tempValDisp.textContent = parseFloat(e.target.value).toFixed(1));
    rainSlider.addEventListener('input', (e) => rainValDisp.textContent = e.target.value);
    humSlider.addEventListener('input', (e) => humValDisp.textContent = e.target.value);

    // Fetch weather when state changes
    stateSelect.addEventListener('change', async () => {
        const state = stateSelect.value;
        if (!state) return;

        loader.classList.remove('hidden');
        try {
            const response = await fetch('/api/predict', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ state })
            });
            const data = await response.json();
            
            if (data.predictions) {
                tempSlider.value = data.predictions.temperature;
                tempValDisp.textContent = data.predictions.temperature.toFixed(1);
                rainSlider.value = data.predictions.rainfall;
                rainValDisp.textContent = Math.round(data.predictions.rainfall);
                humSlider.value = data.predictions.humidity;
                humValDisp.textContent = Math.round(data.predictions.humidity);
            }
        } catch (err) {
            console.error("Error fetching weather:", err);
        } finally {
            loader.classList.add('hidden');
        }
    });

    // Generate Advisory
    generateBtn.addEventListener('click', async () => {
        const state = stateSelect.value;
        const crop = cropSelect.value;
        const season = seasonSelect.value;

        if (!state || !crop || !season) {
            alert("Please select State, Crop, and Season.");
            return;
        }

        loader.classList.remove('hidden');

        try {
            const response = await fetch('/api/predict', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    state, crop, season,
                    temp: parseFloat(tempSlider.value),
                    rain: parseFloat(rainSlider.value),
                    hum: parseFloat(humSlider.value)
                })
            });
            const data = await response.json();

            if (data.error) {
                alert(data.error);
                return;
            }

            updateDashboard(data);
        } catch (err) {
            console.error("Error generating advisory:", err);
            setSafeText('summaryText', `Execution Error: ${err.message}`);
        } finally {
            loader.classList.add('hidden');
        }
    });

    function updateDashboard(data) {
        try {
            const { predictions, benchmark, advisories, alternatives, offline } = data;

            // 1. Banner & Status
            const statusBanner = document.getElementById('statusBanner');
            const summaryText = document.getElementById('summaryText');
            if (statusBanner && summaryText) {
                if (offline) {
                    summaryText.innerHTML = `<i class="fa-solid fa-triangle-exclamation"></i> <strong>Offline Mode:</strong> Dataset averages for ${data.state}.`;
                    statusBanner.className = 'status-banner warning';
                } else {
                    summaryText.innerHTML = `<i class="fa-solid fa-circle-check"></i> Live climate advisory for ${data.state}.`;
                    statusBanner.className = 'status-banner success';
                }
            }
            
            setSafeText('riskText', advisories.risk_assessment);
            setSafeText('irrigationText', advisories.irrigation_management);
            setSafeText('inputGuidanceText', advisories.input_guidance);
            setSafeText('soilNutrientText', advisories.soil_nutrient);

            // Resilience Actions
            const resilienceList = document.getElementById('resilienceActionsList');
            if (resilienceList) {
                resilienceList.innerHTML = '';
                (advisories.resilience_actions || []).forEach(action => {
                    const li = document.createElement('li');
                    li.textContent = action;
                    resilienceList.appendChild(li);
                });
            }

            // Live Alert
            const liveAlertsPanel = document.getElementById('liveAlertsPanel');
            if (data.live_alert && data.live_alert !== "Stable conditions.") {
                if (liveAlertsPanel) liveAlertsPanel.classList.remove('hidden');
                setSafeText('liveAlertText', data.live_alert);
            } else {
                if (liveAlertsPanel) liveAlertsPanel.classList.add('hidden');
            }

            // 2. Benchmarks (Page 1)
            setSafeText('currTemp', predictions.temperature.toFixed(1));
            setSafeText('currRain', Math.round(predictions.rainfall));
            setSafeText('currHum', Math.round(predictions.humidity));
            setSafeText('predYield', predictions.yield ? predictions.yield.toFixed(2) : '--');

            if (benchmark && Object.keys(benchmark).length > 0) {
                setSafeText('histTemp', (benchmark.avg_temp || 0).toFixed(1));
                setSafeText('histRain', (benchmark.avg_rain || 0).toFixed(0));
                setSafeText('histHum', (benchmark.avg_hum || 0).toFixed(0));
                setSafeText('histYield', (benchmark.avg_yield || 0).toFixed(2));

                setSafeText('soilType', benchmark.soil_type || 'N/A');
                setSafeText('co2Val', benchmark.CO2_ppm || '415');
                setSafeText('nitrogenIndex', (benchmark.Nitrogen_availability_index || 0).toFixed(1));
                setSafeText('carbonVal', (benchmark.Carbon_availability_index || 0).toFixed(1));
                setSafeText('oxygenVal', (benchmark.Oxygen_availability_index || 0).toFixed(1));

                // Secondary Stats
                const prod = (benchmark.production || 0).toLocaleString();
                const area = (benchmark.area || 0).toLocaleString();
                const fert = (benchmark.fertilizer || 0).toFixed(1);
                const pest = (benchmark.pesticide || 0).toFixed(1);

                setSafeText('histProd', prod);
                setSafeText('histArea', area);
                setSafeText('histFert', fert);
                setSafeText('histPest', pest);

                setSafeText('areaValue', area + ' ha');
                setSafeText('prodValue', prod);
                setSafeText('fertValue', fert);
                setSafeText('pestValue', pest);
                
                setSafeText('h2oVapor', (benchmark.H2O_vapor_percent || 0).toFixed(1));
                setSafeText('n2Val', (benchmark.N2_percent || 0).toFixed(1));
                setSafeText('o2Val', (benchmark.O2_percent || 0).toFixed(1));

                updateStatus(document.getElementById('tempStatus'), predictions.temperature, benchmark.avg_temp, '°C');
                updateStatus(document.getElementById('rainStatus'), predictions.rainfall, benchmark.avg_rain, 'mm', true);
                updateStatus(document.getElementById('humStatus'), predictions.humidity, benchmark.avg_hum, '%');
            }

            // 3. Resilience Score
            const score = advisories.resilience_score || 0;
            setSafeText('scoreVal', score);
            if (scoreCircle) {
                const offset = 283 - (283 * score) / 100;
                scoreCircle.style.strokeDashoffset = offset;
            }

            // 4. Breakdown Bars
            const breakdown = advisories.breakdown || {};
            animateBar(breakdownBars.temp, breakdown.temp_fit || 0);
            animateBar(breakdownBars.rain, breakdown.rain_fit || 0);
            animateBar(breakdownBars.hum, breakdown.hum_fit || 0);
            animateBar(breakdownBars.nutrient, breakdown.nutrient_fit || 0);

            // 5. Alternatives (Page 3)
            renderAlternatives(alternatives, data.state);

        } catch (err) {
            console.error("Dashboard update failed:", err);
        }
    }

    function renderAlternatives(alternatives, state) {
        setSafeText('altLocation', state);
        const tbody = document.getElementById('alternativesTableBody');
        if (!tbody) return;

        tbody.innerHTML = '';
        if (!alternatives || alternatives.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" style="text-align: center; padding: 30px; color: #666;">No alternative crop data available.</td></tr>';
            return;
        }

        alternatives.forEach(alt => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td><strong>${alt.crop}</strong></td>
                <td>${alt.yield} <small>avg</small></td>
                <td>${alt.soil_type}</td>
                <td>${alt.rainfall} mm</td>
                <td><span class="suitability-badge ${alt.suitability.toLowerCase()}">${alt.suitability}</span></td>
            `;
            tbody.appendChild(tr);
        });
    }

    function updateStatus(el, curr, hist, unit, isRain = false) {
        if (!el || curr === undefined || hist === undefined) return;
        const diff = curr - hist;
        const percentDiff = Math.abs((diff / hist) * 100).toFixed(0);

        if (Math.abs(diff) < (isRain ? 20 : 2)) {
            el.textContent = "≈ Historical";
            el.className = "bench-status match";
        } else {
            const direction = diff > 0 ? "above" : "below";
            el.className = "bench-status diff";
            if (isRain) {
                el.innerHTML = `<i class="fa-solid fa-caret-${diff > 0 ? 'up' : 'down'}"></i> ${percentDiff}% ${direction} hist.`;
            } else {
                el.textContent = `${percentDiff}% ${direction} hist.`;
            }
        }
    }

    function setSafeText(id, val) {
        const el = document.getElementById(id);
        if (el) el.textContent = val !== undefined && val !== null ? val : "N/A";
    }

    function animateBar(obj, val) {
        if (obj && obj.val) obj.val.textContent = val;
        if (obj && obj.bar) obj.bar.style.width = val + "%";
    }
});
