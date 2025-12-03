"""
EcoCompute AI Studio - Carbon-Aware GPU Scheduler
Main Streamlit application combining features from GreenGL Studio and EcoCompute AI.
"""

import os
import sys
from datetime import datetime, timezone, timedelta
import uuid
import time

import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))

from core.carbon_scheduler import scheduler
from core.job_queue import GPUJob, JobStatus
from core.forecast import generate_mock_forecast, get_current_vs_optimal, WindowedForecast, CarbonIntensityPoint

# Page configuration
st.set_page_config(
    page_title="EcoCompute AI Studio",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS combining both projects' styling
st.markdown("""
<style>
    :root {
        --bg-main: #050816;
        --bg-elevated: rgba(15,23,42,0.96);
        --accent: #6366f1;
        --accent-green: #22c55e;
        --accent-red: #ef4444;
        --text-primary: #e5e7eb;
        --text-muted: #9ca3af;
    }

    html, body, [data-testid="stAppViewContainer"] {
        background: radial-gradient(circle at top, #111827 0, #020617 45%, #000000 100%);
        color: var(--text-primary);
    }

    .main .block-container {
        max-width: 1200px;
        padding-top: 1.5rem;
    }

    [data-testid="stSidebar"] {
        background: linear-gradient(145deg, #020617 0%, #111827 100%);
        border-right: 1px solid rgba(75,85,99,0.5);
    }

    .app-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #2E7D32;
        text-align: center;
        margin-bottom: 0.3rem;
    }

    .app-tagline {
        font-size: 1rem;
        color: var(--text-muted);
        text-align: center;
        margin-bottom: 1.5rem;
    }

    .metric-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
        gap: 1rem;
        margin-bottom: 1.5rem;
    }

    .metric-card {
        background: radial-gradient(circle at top left, #1f2937 0, #020617 60%);
        border-radius: 16px;
        border: 1px solid rgba(148,163,184,0.35);
        padding: 1rem;
        transition: transform 0.2s ease;
    }

    .metric-card:hover {
        transform: translateY(-3px);
        border-color: rgba(129,140,248,0.85);
    }

    .metric-label {
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        color: var(--text-muted);
    }

    .metric-value {
        font-size: 1.8rem;
        font-weight: 600;
        color: #f9fafb;
    }

    .green-box {
        background: linear-gradient(135deg, rgba(16,185,129,0.16), rgba(15,23,42,0.96));
        border-radius: 16px;
        border-left: 4px solid #22c55e;
        padding: 1.2rem;
    }

    .red-box {
        background: linear-gradient(135deg, rgba(239,68,68,0.18), rgba(15,23,42,0.96));
        border-radius: 16px;
        border-left: 4px solid #f97373;
        padding: 1.2rem;
    }

    .yellow-box {
        background: linear-gradient(135deg, rgba(251,191,36,0.16), rgba(15,23,42,0.96));
        border-radius: 16px;
        border-left: 4px solid #fbbf24;
        padding: 1.2rem;
    }

    .console-box {
        background-color: #0a0a0a;
        color: #00ff00;
        padding: 20px;
        border-radius: 10px;
        font-family: 'Courier New', monospace;
        font-size: 13px;
        max-height: 400px;
        overflow-y: auto;
        border: 2px solid #00ff00;
        box-shadow: 0 0 10px rgba(0, 255, 0, 0.3);
    }

    .console-header {
        color: #00ffff;
        font-weight: bold;
        border-bottom: 1px solid #00ff00;
        padding-bottom: 10px;
        margin-bottom: 10px;
    }

    .console-log {
        margin: 4px 0;
        line-height: 1.5;
    }

    .stButton>button {
        background-color: #2E7D32;
        color: white;
        font-weight: 600;
        border-radius: 8px;
        border: none;
        padding: 0.5rem 1rem;
    }

    .stButton>button:hover {
        background-color: #1B5E20;
    }
</style>
""", unsafe_allow_html=True)


def create_forecast_chart_with_zones(duration_minutes: int, optimal_time: datetime, region: str = "GB"):
    """Create a line chart showing carbon intensity forecast with RED/GREEN zones."""
    forecast = generate_mock_forecast(region=region, hours=24)
    
    times = [point.datetime for point in forecast]
    intensities = [point.value for point in forecast]
    
    # Thresholds for zones
    DIRTY_THRESHOLD = 200
    CLEAN_THRESHOLD = 120
    
    fig = go.Figure()
    
    # Add zone backgrounds
    fig.add_hrect(
        y0=DIRTY_THRESHOLD,
        y1=max(intensities) + 50,
        fillcolor='rgba(244, 67, 54, 0.1)',
        layer='below',
        line_width=0,
    )
    
    fig.add_hrect(
        y0=0,
        y1=CLEAN_THRESHOLD,
        fillcolor='rgba(76, 175, 80, 0.1)',
        layer='below',
        line_width=0,
    )
    
    fig.add_hrect(
        y0=CLEAN_THRESHOLD,
        y1=DIRTY_THRESHOLD,
        fillcolor='rgba(255, 193, 7, 0.05)',
        layer='below',
        line_width=0,
    )
    
    # Color points based on intensity
    colors = []
    for intensity in intensities:
        if intensity < CLEAN_THRESHOLD:
            colors.append('#4CAF50')
        elif intensity > DIRTY_THRESHOLD:
            colors.append('#f44336')
        else:
            colors.append('#FFC107')
    
    # Add forecast line
    fig.add_trace(go.Scatter(
        x=times,
        y=intensities,
        mode='lines+markers',
        name='Carbon Intensity',
        line=dict(color='#2196F3', width=3),
        marker=dict(size=6, color=colors, line=dict(width=1, color='white')),
        hovertemplate='<b>%{x|%H:%M}</b><br>CI: %{y:.1f} gCO2/kWh<extra></extra>'
    ))
    
    # Highlight optimal window
    optimal_end = optimal_time + timedelta(minutes=duration_minutes)
    fig.add_vrect(
        x0=optimal_time,
        x1=optimal_end,
        fillcolor='rgba(76, 175, 80, 0.25)',
        layer='above',
        line=dict(width=2, color='#2E7D32', dash='dash'),
    )
    
    # Add current time marker
    now = datetime.now(timezone.utc)
    fig.add_shape(
        type='line',
        x0=now, x1=now,
        y0=0, y1=1,
        yref='paper',
        line=dict(color='red', width=2, dash='dash')
    )
    fig.add_annotation(
        x=now, y=1, yref='paper',
        text='⏰ NOW',
        showarrow=False,
        yshift=10,
        font=dict(size=11, color='red')
    )
    
    fig.update_layout(
        title={
            'text': '🌍 Grid Carbon Forecast - Next 24 Hours',
            'x': 0.5,
            'font': {'size': 18, 'color': '#2E7D32'}
        },
        xaxis={'title': 'Time'},
        yaxis={'title': 'Carbon Intensity (gCO2/kWh)'},
        height=450,
        showlegend=False,
        plot_bgcolor='rgba(255,255,255,0.05)',
        paper_bgcolor='rgba(0,0,0,0)',
        hovermode='x unified'
    )
    
    return fig


def create_comparison_chart(ci_now: float, ci_optimal: float, optimal_time: datetime, duration_minutes: int):
    """Create comparison bar chart for dirty vs clean energy."""
    power_kw = 0.3  # Assume 300W
    duration_h = duration_minutes / 60
    
    co2_now = ci_now * power_kw * duration_h
    co2_optimal = ci_optimal * power_kw * duration_h
    
    categories = ['If you run NOW<br>(Current Grid)', f'If you run at {optimal_time.strftime("%I:%M %p")}<br>(Optimal)']
    ci_values = [ci_now, ci_optimal]
    colors = ['#f44336', '#4CAF50']
    
    fig = go.Figure(data=[
        go.Bar(
            x=categories,
            y=ci_values,
            marker_color=colors,
            text=[f'{ci:.1f} gCO2/kWh' for ci in ci_values],
            textposition='outside',
            textfont=dict(size=14)
        )
    ])
    
    fig.update_layout(
        title={
            'text': f'Carbon Impact Comparison - {duration_minutes} Minute Job',
            'x': 0.5,
            'font': {'size': 18, 'color': '#2E7D32'}
        },
        yaxis={'title': 'Carbon Intensity (gCO2/kWh)'},
        height=400,
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
    )
    
    return fig, co2_now, co2_optimal


def generate_simulation_logs(optimal_time: datetime, ci_now: float, ci_optimal: float, duration_minutes: int):
    """Generate console logs showing scheduler in action."""
    now = datetime.now(timezone.utc).astimezone()
    optimal_local = optimal_time.astimezone() if optimal_time.tzinfo else optimal_time
    
    logs = []
    logs.append(f"[{now.strftime('%I:%M %p')}] 🚀 EcoCompute AI Scheduler initialized")
    logs.append(f"[{now.strftime('%I:%M %p')}] 📊 Analyzing grid carbon intensity...")
    logs.append(f"[{now.strftime('%I:%M %p')}] ⚡ Current grid status: {ci_now:.0f} gCO2/kWh")
    
    if ci_now > 180:
        logs.append(f"[{now.strftime('%I:%M %p')}] 🔴 WARNING: Grid is DIRTY ({ci_now:.0f}g/kWh)")
        logs.append(f"[{now.strftime('%I:%M %p')}] ⏸️  Job execution PAUSED (fossil fuel heavy)")
        logs.append(f"[{now.strftime('%I:%M %p')}] 💤 Putting GPU to sleep...")
    else:
        logs.append(f"[{now.strftime('%I:%M %p')}] 🟡 Grid is MODERATE ({ci_now:.0f}g/kWh)")
    
    logs.append(f"[{now.strftime('%I:%M %p')}] 🔍 Scanning next 24 hours for clean energy...")
    logs.append(f"[{now.strftime('%I:%M %p')}] ✨ Found optimal window: {optimal_local.strftime('%I:%M %p')}")
    logs.append(f"[{now.strftime('%I:%M %p')}] 🟢 Expected CI: {ci_optimal:.0f}g/kWh (CLEAN ENERGY!)")
    
    delay = optimal_time - datetime.now(timezone.utc)
    delay_hours = delay.total_seconds() / 3600
    
    if delay_hours > 0.5:
        logs.append(f"[{now.strftime('%I:%M %p')}] ⏰ Scheduling for {optimal_local.strftime('%I:%M %p')} ({delay_hours:.1f}h delay)")
        logs.append(f"[{now.strftime('%I:%M %p')}] 💾 Job state saved")
        logs.append("")
        logs.append(f"[{optimal_local.strftime('%I:%M %p')}] ⏰ WAKE UP! Optimal window reached")
        logs.append(f"[{optimal_local.strftime('%I:%M %p')}] 🌞 Grid powered by RENEWABLES")
        logs.append(f"[{optimal_local.strftime('%I:%M %p')}] 🚀 Resuming job execution")
    else:
        logs.append(f"[{now.strftime('%I:%M %p')}] 🚀 Optimal window is NOW! Starting job...")
    
    end_time = optimal_local + timedelta(minutes=duration_minutes)
    logs.append(f"[{optimal_local.strftime('%I:%M %p')}] 📊 Job progress: 0% → 100%")
    logs.append(f"[{end_time.strftime('%I:%M %p')}] ✅ Job completed successfully!")
    
    # Calculate savings
    power_kw = 0.3
    duration_h = duration_minutes / 60
    co2_now = ci_now * power_kw * duration_h
    co2_optimal = ci_optimal * power_kw * duration_h
    savings = co2_now - co2_optimal
    
    logs.append(f"[{end_time.strftime('%I:%M %p')}] 🌱 Carbon saved: {savings:.1f}g CO2")
    logs.append(f"[{end_time.strftime('%I:%M %p')}] 🎉 Efficiency: {((savings/co2_now)*100):.0f}% reduction")
    logs.append(f"[{end_time.strftime('%I:%M %p')}] 💚 Thank you for being carbon-aware!")
    
    return logs


def main():
    # Header
    st.markdown('<div class="app-header">🌱 EcoCompute AI Studio</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="app-tagline">Carbon-aware compute scheduling - Run your jobs when the grid is greenest</div>',
        unsafe_allow_html=True
    )
    
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Configuration")
        region = st.selectbox(
            "Select Region",
            ["GB", "IN", "US", "DE", "NO", "AU", "FR"],
            help="Select your electricity grid region"
        )
        
        region_names = {
            "GB": "🇬🇧 United Kingdom",
            "IN": "🇮🇳 India",
            "US": "🇺🇸 United States",
            "DE": "🇩🇪 Germany",
            "NO": "🇳🇴 Norway",
            "AU": "🇦🇺 Australia",
            "FR": "🇫🇷 France"
        }
        st.info(f"Region: {region_names.get(region, region)}")
        
        st.divider()
        
        st.markdown("### Carbon Intensity Guide")
        st.markdown("""
        - 🟢 **< 120**: Excellent (Renewables)
        - 🟡 **120-200**: Moderate (Mixed)
        - 🔴 **> 200**: Poor (Fossil heavy)
        """)
        
        st.divider()
        
        if st.button("🔄 Refresh Data"):
            st.rerun()
    
    # Main tabs
    tabs = st.tabs([
        "📊 Dashboard",
        "🌍 Schedule Job",
        "📋 Job Queue",
        "📈 Analytics",
        "🌐 Region Comparison"
    ])
    
    # TAB 1: Dashboard
    with tabs[0]:
        stats = scheduler.get_dashboard_stats()
        
        # Grid status
        grid_status = scheduler.carbon_provider.get_grid_carbon_intensity(region)
        intensity = grid_status['carbonIntensity']
        greenness = grid_status['greenness']
        
        # Metrics grid
        st.markdown(f"""
        <div class="metric-grid">
            <div class="metric-card">
                <div class="metric-label">Total Jobs</div>
                <div class="metric-value">{stats['total_jobs_submitted']}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">In Queue</div>
                <div class="metric-value">{stats['pending'] + stats['scheduled']}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Completed</div>
                <div class="metric-value">{stats['completed']}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">CO₂ Tracked</div>
                <div class="metric-value">{stats['total_emissions_kg']:.3f} kg</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        st.divider()
        
        # Grid status display
        col1, col2 = st.columns(2)
        
        with col1:
            if greenness == "HIGH":
                st.markdown(f"""
                <div class="green-box">
                    <h3>✅ Grid is CLEAN!</h3>
                    <h2 style="color: #22c55e;">{intensity:.0f} gCO2/kWh</h2>
                    <p><strong>Recommendation:</strong> Run GPU jobs NOW!</p>
                </div>
                """, unsafe_allow_html=True)
            elif greenness == "MEDIUM":
                st.markdown(f"""
                <div class="yellow-box">
                    <h3>⏳ Grid is MODERATE</h3>
                    <h2 style="color: #fbbf24;">{intensity:.0f} gCO2/kWh</h2>
                    <p><strong>Recommendation:</strong> Consider waiting for cleaner hours</p>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div class="red-box">
                    <h3>❌ Grid is DIRTY</h3>
                    <h2 style="color: #ef4444;">{intensity:.0f} gCO2/kWh</h2>
                    <p><strong>Recommendation:</strong> Defer non-urgent jobs</p>
                </div>
                """, unsafe_allow_html=True)
        
        with col2:
            # Gauge chart
            fig = go.Figure(data=[go.Indicator(
                mode="gauge+number+delta",
                value=intensity,
                title={'text': "Carbon Intensity"},
                delta={'reference': 200},
                gauge={
                    'axis': {'range': [0, 800]},
                    'bar': {'color': "darkblue"},
                    'steps': [
                        {'range': [0, 120], 'color': "#90EE90"},
                        {'range': [120, 200], 'color': "#FFD700"},
                        {'range': [200, 800], 'color': "#FF6B6B"}
                    ],
                    'threshold': {
                        'line': {'color': "red", 'width': 4},
                        'thickness': 0.75,
                        'value': 200
                    }
                }
            )])
            fig.update_layout(height=280, margin=dict(t=50, b=20))
            st.plotly_chart(fig, use_container_width=True)
        
        # Actions
        st.divider()
        col_a1, col_a2 = st.columns(2)
        
        with col_a1:
            if st.button("🎯 Schedule All Pending Jobs", use_container_width=True):
                result = scheduler.schedule_pending_jobs(region)
                st.success(f"Scheduled {result['scheduled_count']} jobs, deferred {result['deferred_count']}")
        
        with col_a2:
            if st.button("▶️ Run Next Scheduled Job", use_container_width=True):
                scheduled_jobs = scheduler.job_queue.get_jobs_by_status(JobStatus.SCHEDULED.value)
                if scheduled_jobs:
                    result = scheduler.run_scheduled_job(scheduled_jobs[0].job_id)
                    if 'error' not in result:
                        st.success(f"Job completed: {result['emissions_kg_co2']:.4f} kg CO₂")
                    else:
                        st.error(result['error'])
                else:
                    st.warning("No scheduled jobs to run")
    
    # TAB 2: Schedule Job (GreenGL-style)
    with tabs[1]:
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.markdown("### 📁 Upload Script (Optional)")
            uploaded_file = st.file_uploader(
                "Choose a Python file (.py)",
                type=['py'],
                help="Upload the Python script you want to schedule"
            )
            
            if uploaded_file is not None:
                st.success(f"✅ Loaded: {uploaded_file.name}")
                with st.expander("📄 Preview Script"):
                    file_content = uploaded_file.read().decode('utf-8')
                    st.code(file_content, language='python')
                    uploaded_file.seek(0)
        
        with col2:
            st.markdown("### ⏱️ Job Configuration")
            job_name = st.text_input("Job Name", f"job_{uuid.uuid4().hex[:6]}")
            duration_minutes = st.slider(
                "Expected Duration (minutes)",
                min_value=15,
                max_value=480,
                value=60,
                step=15
            )
            power_draw = st.slider(
                "GPU Power Draw (watts)",
                min_value=100,
                max_value=700,
                value=300
            )
            priority = st.slider("Priority (1=low, 5=high)", 1, 5, 3)
            carbon_threshold = st.slider("Carbon Threshold (gCO2/kWh)", 100, 500, 200)
        
        st.markdown("---")
        
        col_btn1, col_btn2, col_btn3 = st.columns([1, 2, 1])
        with col_btn2:
            schedule_btn = st.button("🌍 Schedule Job", use_container_width=True)
        
        if schedule_btn:
            with st.spinner("🔍 Finding the greenest time..."):
                # Create job
                job = GPUJob(
                    job_id=str(uuid.uuid4())[:8],
                    name=job_name,
                    duration_minutes=duration_minutes,
                    power_draw_watts=power_draw,
                    priority=priority,
                    carbon_intensity_threshold=carbon_threshold,
                    region=region,
                    script_content=uploaded_file.read().decode('utf-8') if uploaded_file else None
                )
                scheduler.job_queue.add_job(job)
                
                # Get scheduling info
                result = scheduler.schedule_single_job(job, region=region)
                st.session_state.schedule_result = result
        
        # Display results
        if 'schedule_result' in st.session_state:
            result = st.session_state.schedule_result
            
            st.markdown("---")
            st.markdown("## 📊 Scheduling Results")
            
            # Metrics
            col_m1, col_m2, col_m3, col_m4 = st.columns(4)
            
            optimal_time = result['optimal_time']
            if isinstance(optimal_time, str):
                optimal_time = datetime.fromisoformat(optimal_time)
            
            with col_m1:
                st.metric(
                    label="🕐 Optimal Start",
                    value=optimal_time.strftime("%I:%M %p"),
                    delta=optimal_time.strftime('%b %d')
                )
            
            with col_m2:
                st.metric(
                    label="⏳ Delay",
                    value=f"{result['delay_hours']:.1f}h",
                    delta="Wait" if result['delay_hours'] > 0.5 else "Now!"
                )
            
            with col_m3:
                st.metric(
                    label="💰 Carbon Savings",
                    value=f"{result['savings_percent']:.1f}%",
                    delta=f"-{result['savings_g']:.1f}g"
                )
            
            with col_m4:
                if result['ci_optimal'] < 120:
                    rating = "🟢 Excellent"
                elif result['ci_optimal'] < 200:
                    rating = "🟡 Good"
                else:
                    rating = "🔴 Fair"
                st.metric(label="📈 Rating", value=rating)
            
            # Comparison chart
            st.markdown("### 🔄 Dirty vs Clean Comparison")
            fig_comp, co2_now, co2_opt = create_comparison_chart(
                result['ci_now'],
                result['ci_optimal'],
                optimal_time,
                result['duration_minutes']
            )
            st.plotly_chart(fig_comp, use_container_width=True)
            
            # Detailed cards
            col_c1, col_c2 = st.columns(2)
            with col_c1:
                st.markdown(f"""
                <div class="red-box">
                    <h4>🔴 If you run NOW</h4>
                    <p>Carbon Intensity: <b>{result['ci_now']:.1f}</b> gCO2/kWh</p>
                    <p>Estimated CO2: <b>{result['emissions_now_g']:.2f}g</b></p>
                </div>
                """, unsafe_allow_html=True)
            
            with col_c2:
                st.markdown(f"""
                <div class="green-box">
                    <h4>🟢 At Optimal Time</h4>
                    <p>Carbon Intensity: <b>{result['ci_optimal']:.1f}</b> gCO2/kWh</p>
                    <p>Estimated CO2: <b>{result['emissions_optimal_g']:.2f}g</b></p>
                    <p>Savings: <b>{result['savings_g']:.2f}g</b> ({result['savings_percent']:.1f}%)</p>
                </div>
                """, unsafe_allow_html=True)
            
            # Forecast chart
            st.markdown("### 📈 Grid Carbon Forecast")
            fig_forecast = create_forecast_chart_with_zones(
                result['duration_minutes'],
                optimal_time,
                region
            )
            st.plotly_chart(fig_forecast, use_container_width=True)
            
            # Live console
            st.markdown("### 🖥️ Live Scheduler Console")
            logs = generate_simulation_logs(
                optimal_time,
                result['ci_now'],
                result['ci_optimal'],
                result['duration_minutes']
            )
            
            console_html = '<div class="console-box">'
            console_html += '<div class="console-header">🌿 EcoCompute AI Scheduler v1.0</div>'
            for log in logs:
                if log == "":
                    console_html += '<div class="console-log">&nbsp;</div>'
                else:
                    console_html += f'<div class="console-log">{log}</div>'
            console_html += '</div>'
            st.markdown(console_html, unsafe_allow_html=True)
            
            # Replay button
            if st.button("🎬 Replay Simulation"):
                replay_container = st.empty()
                displayed = []
                for log in logs:
                    if log != "":
                        displayed.append(log)
                        html = '<div class="console-box"><div class="console-header">🌿 Live Simulation</div>'
                        html += ''.join(f'<div class="console-log">{l}</div>' for l in displayed)
                        html += '</div>'
                        replay_container.markdown(html, unsafe_allow_html=True)
                        time.sleep(0.3)
            
            if st.button("🔄 Schedule Another Job"):
                del st.session_state.schedule_result
                st.rerun()
    
    # TAB 3: Job Queue
    with tabs[2]:
        st.subheader("📋 Job Queue Status")
        
        # Submit new job form
        with st.expander("➕ Submit New Job"):
            col1, col2 = st.columns(2)
            with col1:
                new_name = st.text_input("Job Name", f"manual_job_{uuid.uuid4().hex[:4]}")
                new_duration = st.slider("Duration (min)", 5, 480, 60, key="new_dur")
            with col2:
                new_power = st.slider("Power (W)", 100, 700, 300, key="new_pow")
                new_priority = st.slider("Priority", 1, 5, 3, key="new_pri")
            
            if st.button("➕ Submit", key="submit_manual"):
                new_job = GPUJob(
                    job_id=str(uuid.uuid4())[:8],
                    name=new_name,
                    duration_minutes=new_duration,
                    power_draw_watts=new_power,
                    priority=new_priority,
                    region=region
                )
                scheduler.job_queue.add_job(new_job)
                st.success(f"✅ Job submitted: {new_job.job_id}")
                st.rerun()
        
        # Job status tabs
        status_tabs = st.tabs(["⏳ Pending", "📅 Scheduled", "▶️ Running", "✅ Completed", "⏸️ Deferred"])
        statuses = [
            JobStatus.PENDING.value,
            JobStatus.SCHEDULED.value,
            JobStatus.RUNNING.value,
            JobStatus.COMPLETED.value,
            JobStatus.DEFERRED.value
        ]
        
        for tab, status in zip(status_tabs, statuses):
            with tab:
                jobs = scheduler.job_queue.get_jobs_by_status(status)
                if jobs:
                    df = pd.DataFrame([{
                        'Job ID': j.job_id,
                        'Name': j.name,
                        'Duration': f"{j.duration_minutes}m",
                        'Power': f"{j.power_draw_watts}W",
                        'Priority': j.priority,
                        'Submitted': j.submitted_at[:16] if j.submitted_at else "-",
                    } for j in jobs])
                    st.dataframe(df, use_container_width=True)
                else:
                    st.info(f"No {status} jobs")
    
    # TAB 4: Analytics
    with tabs[3]:
        st.subheader("📈 Emissions Analytics")
        
        emissions = scheduler.emissions_tracker.get_emissions_summary()
        
        col1, col2 = st.columns(2)
        with col1:
            fig = go.Figure(data=[go.Indicator(
                mode="number+delta",
                value=emissions['total_emissions_kg'] * 1000,
                title="Total CO₂ Tracked (grams)",
                number={'suffix': 'g'}
            )])
            fig.update_layout(height=250)
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            if emissions['total_jobs'] > 0:
                fig = go.Figure(data=[go.Indicator(
                    mode="gauge+number",
                    value=emissions['avg_emissions_per_job_kg'] * 1000,
                    title="Avg CO₂ per Job (g)",
                    gauge={'axis': {'range': [0, 500]}}
                )])
                fig.update_layout(height=250)
                st.plotly_chart(fig, use_container_width=True)
        
        # Emissions log
        log = scheduler.emissions_tracker.emissions_log
        if log:
            st.subheader("Emissions History")
            df = pd.DataFrame(log)
            if 'timestamp' in df.columns:
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                df = df.sort_values('timestamp')
                
                fig = px.line(
                    df, x='timestamp', y='emissions_kg_co2',
                    title="Emissions Over Time",
                    markers=True
                )
                st.plotly_chart(fig, use_container_width=True)
    
    # TAB 5: Region Comparison
    with tabs[4]:
        st.subheader("🌍 Multi-Region Carbon Intensity")
        
        regions_list = ["IN", "US", "DE", "NO", "AU", "GB", "FR"]
        comparison = scheduler.carbon_provider.get_multi_region_comparison(regions_list)
        
        region_data = []
        for code, data in comparison['regions'].items():
            region_data.append({
                'Region': code,
                'Carbon Intensity': data['carbonIntensity'],
                'Greenness': data['greenness'],
                'Recommendation': data['recommendation']
            })
        
        df = pd.DataFrame(region_data)
        
        fig = px.bar(
            df, x='Region', y='Carbon Intensity',
            color='Greenness',
            color_discrete_map={'HIGH': '#4CAF50', 'MEDIUM': '#FFC107', 'LOW': '#f44336'},
            title="Carbon Intensity by Region"
        )
        st.plotly_chart(fig, use_container_width=True)
        
        st.dataframe(df, use_container_width=True)
        
        st.success(
            f"**Greenest Region:** {comparison['greenest_region']} "
            f"({comparison['greenest_intensity']:.0f} gCO2/kWh)"
        )
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: #666; padding: 1rem;'>
        🌱 <b>EcoCompute AI Studio</b> | Carbon-Aware GPU Scheduling<br>
        <i>Reducing compute emissions, one job at a time</i>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
