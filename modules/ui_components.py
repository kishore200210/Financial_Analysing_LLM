"""
UI Components Module
Contains styling, helper functions, and reusable UI elements for the Financial Analyzer App.
"""
import streamlit as st

def apply_custom_style():
    """Apply global CSS styles."""
    st.markdown("""
    <style>
        /* ---------- Global Dark Theme ---------- */
        .stApp {
            background: radial-gradient(circle at top right, #1a1a2e, #16213e, #0f0c29);
            color: #e0e0e0;
            font-family: 'Inter', sans-serif;
        }

        /* ---------- Header ---------- */
        .app-header {
            text-align: center;
            padding: 2.5rem 1rem 2rem;
            background: linear-gradient(135deg, rgba(16,185,129,0.1), rgba(59,130,246,0.1));
            border-radius: 20px;
            margin-bottom: 2rem;
            border: 1px solid rgba(255,255,255,0.05);
            backdrop-filter: blur(15px);
            box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.3);
        }
        .app-header h1 {
            background: linear-gradient(90deg, #10b981, #3b82f6, #8b5cf6);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            font-size: 3rem;
            font-weight: 900;
            margin: 0;
            letter-spacing: -0.02em;
        }
        .app-header p {
            color: #94a3b8;
            font-size: 1.1rem;
            margin-top: 0.6rem;
            font-weight: 300;
        }

        /* ---------- Metric Cards ---------- */
        div[data-testid="stMetric"] {
            background: rgba(255,255,255,0.03);
            border: 1px solid rgba(255,255,255,0.07);
            border-radius: 16px;
            padding: 1.2rem;
            backdrop-filter: blur(10px);
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        }
        div[data-testid="stMetric"]:hover {
            transform: translateY(-5px) scale(1.02);
            background: rgba(255,255,255,0.05);
            border-color: rgba(16,185,129,0.3);
            box-shadow: 0 12px 40px rgba(0, 0, 0, 0.4);
        }
        div[data-testid="stMetric"] label {
            color: #94a3b8 !important;
            font-weight: 500;
            text-transform: uppercase;
            font-size: 0.8rem;
            letter-spacing: 0.1em;
        }
        div[data-testid="stMetric"] [data-testid="stMetricValue"] {
            color: #ffffff !important;
            font-weight: 800;
            font-size: 2rem !important;
        }

        /* ---------- Sidebar ---------- */
        section[data-testid="stSidebar"] {
            background: rgba(10, 10, 26, 0.98) !important;
            border-right: 1px solid rgba(255,255,255,0.05);
        }
        .sidebar-title {
            font-size: 1.5rem;
            font-weight: 800;
            background: linear-gradient(90deg, #10b981, #3b82f6);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 1rem;
        }

        /* ---------- Buttons ---------- */
        .stButton > button {
            width: 100%;
            border-radius: 12px;
            font-weight: 600;
            padding: 0.6rem 1rem;
            transition: all 0.3s ease;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }
        .stButton > button[kind="primary"] {
            background: linear-gradient(135deg, #10b981, #3b82f6) !important;
            border: none !important;
            color: white !important;
        }
        .stButton > button:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(16,185,129,0.3);
            filter: brightness(1.1);
        }

        /* ---------- AI response card ---------- */
        .ai-response-container {
            background: rgba(255, 255, 255, 0.02);
            border-left: 4px solid #10b981;
            border-radius: 12px;
            padding: 1.5rem;
            margin: 1rem 0;
            animation: fadeIn 0.5s ease-out;
        }
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        /* ---------- Dataframe Styles ---------- */
        .stDataFrame {
            border-radius: 12px;
            overflow: hidden;
            border: 1px solid rgba(255,255,255,0.05);
        }
    </style>
    """, unsafe_allow_html=True)

def render_header():
    """Render the application header."""
    st.markdown("""
    <div class="app-header">
        <h1>💰 Financial Analyzer AI</h1>
        <p>Your intelligent companion for multi-app UPI statement analysis & personalized financial growth.</p>
    </div>
    """, unsafe_allow_html=True)

def render_sidebar():
    """Render the sidebar and return user inputs."""
    with st.sidebar:
        st.markdown('<p class="sidebar-title">💰 Financial AI</p>', unsafe_allow_html=True)
        st.markdown("Transform raw statements into actionable wealth insights.")
        st.markdown("---")

        st.subheader("📤 Data Input")
        uploaded_file = st.file_uploader("Upload UPI PDF", type=["pdf"], label_visibility="collapsed")

        st.markdown("---")
        st.subheader("🧠 Intelligence Engine")

        analysis_mode = st.selectbox(
            "Select Model Strategy",
            ["Advanced Agent (Gemini)", "Custom Langflow"],
            index=0,
        )

        api_key = ""
        langflow_url = ""
        langflow_key = ""

        if "Gemini" in analysis_mode:
            api_key = st.text_input(
                "Gemini API Key",
                type="password",
                placeholder="Enter your Google Gemini API key",
            )
        else:
            langflow_url = st.text_input(
                "Langflow Endpoint",
                placeholder="http://localhost:7860/api/v1/run/<flow_id>",
            )
            langflow_key = st.text_input(
                "Langflow API Key",
                type="password",
                placeholder="Enter your Langflow API Key",
            )

        st.markdown("---")
        st.markdown("### 🏦 Multi-App Support")
        st.caption("✅ Paytm  ✅ PhonePe  ✅ Google Pay")
        
        return uploaded_file, analysis_mode, api_key, langflow_url, langflow_key

def render_metrics(total_spend, total_income, txn_count):
    """Render the top 3 KPI cards with enhanced styling."""
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("💸 Monthly Spend", f"₹{total_spend:,.0f}")
    with col2:
        st.metric("💰 Total Credits", f"₹{total_income:,.0f}")
    with col3:
        st.metric("📈 Activity", f"{txn_count} Txns")

def render_ai_response(insight):
    """Render the AI response in a premium container."""
    st.markdown(
        f'<div class="ai-response-container">{insight}</div>',
        unsafe_allow_html=True,
    )

def render_footer():
    """Render the footer tip."""
    st.markdown("---")
    st.markdown(
        '<div style="text-align: center; color: #64748b; font-size: 0.9rem; padding: 1rem;">🚀 Built with LangFlow, Streamlit & Gemini AI</div>',
        unsafe_allow_html=True,
    )

def format_plotly_fig(fig):
    """Apply consistent dark premium styling to a Plotly figure."""
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#94a3b8", family="Inter"),
        margin=dict(l=10, r=10, t=40, b=10),
        hovermode="x unified",
        showlegend=True,
    )
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=True, gridcolor="rgba(255,255,255,0.05)")
    return fig
