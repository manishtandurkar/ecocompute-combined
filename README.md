# 🌱 EcoCompute AI - Carbon-Aware GPU Scheduler

**Make your AI training greener by running when the grid is cleanest!**

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![Streamlit](https://img.shields.io/badge/Streamlit-1.28+-red)
![License](https://img.shields.io/badge/License-MIT-green)

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run EcoCompute AI Studio
```bash
streamlit run app.py
```

The app will open automatically at `http://localhost:8501`

## 📋 Project Structure

```
combined/
├── app.py                      # Main Streamlit application
├── requirements.txt            # All dependencies
├── sample_ml_script.py         # Example script for testing
├── core/
│   ├── __init__.py
│   ├── carbon_api.py           # Multi-source carbon intensity API
│   ├── carbon_scheduler.py     # Main scheduling logic
│   ├── emissions_tracker.py    # CodeCarbon integration
│   ├── job_queue.py            # Job queue management
│   └── forecast.py             # Windowed forecast algorithm
├── cats/
│   ├── __init__.py
│   ├── forecast.py             # CATS WindowedForecast
│   ├── CI_api_interface.py     # Carbon intensity API interface
│   ├── CI_api_query.py         # API query utilities
│   ├── carbonFootprint.py      # Footprint calculations
│   ├── constants.py            # Constants and configurations
│   ├── configure.py            # Configuration management
│   └── config.yml              # Hardware profiles
└── data/                       # Data storage for jobs and emissions
```

## 🎯 Features

### From GreenGL Studio (ManishHP)
- 🌍 **24-hour carbon intensity forecast** with RED/GREEN zones
- 🖥️ **Live simulation console** showing scheduler in action
- 📊 **Interactive charts** comparing "dirty" vs "clean" energy
- 💰 **Carbon savings calculator** (typically 60-70% reduction)
- 🎬 **Replay animation** for demos
- 📁 **Simple file upload** for Python scripts
- ✨ **WindowedForecast algorithm** for optimal scheduling

### From EcoCompute AI (ChetanP)
- 📋 **Job Queue Management** with priorities
- 🌐 **Multi-region carbon intensity comparison** (IN, US, DE, NO, AU)
- 📈 **Emissions tracking** with CodeCarbon integration
- 📊 **Analytics dashboard** with cumulative emissions
- ⚡ **Real-time grid status** with recommendations
- 🔄 **Automatic job deferral** based on carbon intensity thresholds

## 🎬 Demo Instructions

### For Hackathon Judges:
1. Run `streamlit run app.py`
2. Go to **Schedule Job** tab
3. Upload `sample_ml_script.py` or submit a job manually
4. Set duration to 60 minutes
5. Click "🌍 Schedule Job"
6. See the magic:
   - RED ZONE (dirty grid) vs GREEN ZONE (clean grid)
   - Live console logs showing GPU sleeping/waking
   - Carbon savings percentage

### Key Demo Points:
- **NOW** = Red zone (high gCO2/kWh) - Fossil fuels
- **Optimal Time** = Green zone (low gCO2/kWh) - Renewables
- **Savings** = 60-70% CO2 reduction just by timing!

## 📦 Dependencies

### Core
- **streamlit** - Web UI framework
- **plotly** - Interactive charts
- **pandas** - Data handling
- **requests** - API calls
- **requests-cache** - API caching
- **PyYAML** - Configuration
- **codecarbon** - Emissions tracking (optional)

## 🌍 Environmental Impact

By scheduling computational jobs during periods of lower carbon intensity:
- Reduce carbon footprint by 60-70%
- No code changes required
- Automatic optimization based on grid status

---

**EcoCompute AI**  
*Reducing compute emissions, one job at a time* 🌍  
Built for Hackathon
