import streamlit as st
import pandas as pd
import tempfile
import os
import plotly.express as px
from modules.pdf_parser import parse_pdf
from modules.data_cleaner import clean_data
from modules.analyzer import calculate_stats, get_llm_insights

# Page Config
st.set_page_config(page_title="Financial Analyzer AI", page_icon="💰", layout="wide")

# Custom CSS
st.markdown("""
<style>
    .main {
        background-color: #f5f5f5;
    }
    .stButton>button {
        width: 100%;
    }
</style>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.title("💰 Financial AI")
    st.markdown("Upload your UPI statement PDF to analyze your spending.")
    
    analysis_mode = st.radio("Analysis Mode", ["Internal AI (Gemini)", "Langflow API"])
    
    api_key = ""
    langflow_url = ""
    
    if analysis_mode == "Internal AI (Gemini)":
        api_key = st.text_input("Google Gemini API Key", type="password", help="Required for AI insights")
    else:
        langflow_url = st.text_input("Langflow API Endpoint", placeholder="http://localhost:7860/api/v1/run/<flow_id>")
    
    uploaded_file = st.file_uploader("Upload PDF Statement", type=['pdf'])
    
    st.markdown("---")
    st.info("Supported formats: Paytm, PhonePe, GPay PDFs (standard formats).")

# Main Content
if uploaded_file:
    # Save to temp file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
        tmp_file.write(uploaded_file.getvalue())
        tmp_path = tmp_file.name

    try:
        with st.spinner("Parsing PDF..."):
            raw_data = parse_pdf(tmp_path)
            
        # Clean Data
        df = clean_data(raw_data)
        
        # Remove temp file
        os.remove(tmp_path)
        
        if df.empty:
            st.error("Could not extract any transactions. Please check the PDF format.")
        else:
            # Stats
            stats = calculate_stats(df)
            
            st.header("📊 Financial Dashboard")
            
            col1, col2, col3 = st.columns(3)
            col1.metric("Total Spend", f"₹{stats['total_spend']:,.2f}")
            col2.metric("Total Income", f"₹{stats['total_income']:,.2f}")
            col3.metric("Transactions", stats['transaction_count'])
            
            # Charts
            st.subheader("Spending Trends")
            
            # Daily Trend
            daily = df.groupby('Date')['Amount'].sum().reset_index()
            fig_daily = px.line(daily, x='Date', y='Amount', title="Daily Transaction Volume")
            st.plotly_chart(fig_daily, use_container_width=True)
            
            # Category Breakdown (if available, otherwise Description)
            st.subheader("Category / Description Analysis")
            # Identify spending (Debit) for charts
            spending_df = df[df['Direction'].str.upper().isin(['DR', 'DEBIT', 'UNKNOWN'])] 
            # If Unknown, we often assume spend if not explicitly Credit, but let's be careful.
            
            if not spending_df.empty:
                # Group by Description since Category might be empty initially
                top_desc = spending_df.groupby('Description')['Amount'].sum().sort_values(ascending=False).head(10).reset_index()
                fig_desc = px.pie(top_desc, names='Description', values='Amount', title="Top 10 Spending Sources")
                st.plotly_chart(fig_desc, use_container_width=True)

            # Data Table
            with st.expander("View Raw Data"):
                st.dataframe(df)
                
            # AI Section
            st.divider()
            st.header("🤖 AI Financial Advisor")
            
            if analysis_mode == "Internal AI (Gemini)" and not api_key:
                st.warning("Please enter your Google Gemini API Key in the sidebar.")
            elif analysis_mode == "Langflow API" and not langflow_url:
                st.warning("Please enter your Langflow API URL in the sidebar.")
            else:
                user_query = st.text_area("Ask about your finances:", "What are my biggest wasteful spending habits?")
                
                if st.button("Analyze with AI"):
                    with st.spinner("AI is thinking..."):
                        if analysis_mode == "Internal AI (Gemini)":
                            insight = get_llm_insights(df, api_key, user_query)
                        else:
                            # For Langflow, we construct a message with context + query
                            from modules.analyzer import calculate_stats, call_langflow_api
                            stats = calculate_stats(df)
                            top_transactions = df.sort_values(by='Amount', ascending=False).head(20).to_string(index=False)
                            context_str = f"Summary: {stats}\nTop Trans: {top_transactions}"
                            full_prompt = f"Context: {context_str}\n\nQuestion: {user_query}"
                            
                            insight = call_langflow_api(full_prompt, langflow_url)
                            
                        st.markdown(insight)

    except Exception as e:
        st.error(f"An error occurred: {e}")
        # Clean up temp file if exists
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

else:
    st.header("Welcome to Financial Analyzer AI")
    st.write("Please upload a PDF to get started.")
    st.markdown("""
    ### How it works:
    1. **Upload** your UPI PDF statement.
    2. **View** instant statistical dashboard.
    3. **Chat** with the AI to get personalized advice.
    """)
