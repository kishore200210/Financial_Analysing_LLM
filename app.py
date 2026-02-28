"""
Streamlit App for Financial Analyzer AI
Interactive dashboard for UPI transaction analysis with LLM insights.
"""
import streamlit as st
import pandas as pd
import tempfile
import os

import plotly.express as px
from modules.pdf_parser import parse_pdf
from modules.data_cleaner import clean_data
from modules.analyzer import calculate_stats, get_llm_insights, call_langflow_api
from modules.transaction_classifier import TransactionClassifier
from modules.ui_components import (
    apply_custom_style, render_header, render_sidebar, 
    render_metrics, render_ai_response, render_footer, format_plotly_fig
)

# Initialize Classifier (rule-based by default for speed)
classifier = TransactionClassifier(use_ml=False)

# ── Page Config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Financial Analyzer AI",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Apply global styles
apply_custom_style()

# Render Header
render_header()

# Render Sidebar & Get Inputs
uploaded_file, analysis_mode, api_key, langflow_url, langflow_key = render_sidebar()


# ── Main Content ─────────────────────────────────────────────────────────────
if uploaded_file is not None:
    # Save uploaded file to a temp path so pdfplumber can open it
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(uploaded_file.getvalue())
        tmp_path = tmp.name

    try:
        # ── Parse & Clean ────────────────────────────────────────────────
        with st.spinner("📄 Parsing PDF…"):
            raw_data = parse_pdf(tmp_path)
            df = clean_data(raw_data)

        # Clean up temp file
        os.remove(tmp_path)

        if df.empty:
            st.error("❌ No transactions found in the PDF. Please check the format.")
        else:
            # ── Classify transactions ────────────────────────────────────
            df = classifier.classify_dataframe(df)

            # ── Stats ────────────────────────────────────────────────────
            stats = calculate_stats(df)
            total_spend = stats.get("total_spend", 0)
            total_income = stats.get("total_income", 0)
            txn_count = stats.get("transaction_count", 0)

            # ── KPI Cards ────────────────────────────────────────────────
            st.success("✅ PDF processed successfully!")
            render_metrics(total_spend, total_income, txn_count)
            st.markdown("")  # spacer

            # ── Tabs: Daily Trend | Category Breakdown | Transaction Data ─
            tab_daily, tab_cat, tab_data = st.tabs(
                ["📈 Daily Trend", "🥧 Category Breakdown", "📊 Transaction Data"]
            )

            # ── Tab 1: Daily Trend ───────────────────────────────────────
            with tab_daily:
                daily = df.groupby("Date")["Amount"].sum().reset_index()
                fig_daily = px.line(
                    daily,
                    x="Date",
                    y="Amount",
                    title="Daily Transaction Volume",
                    markers=True,
                )
                fig_daily.update_traces(
                    line=dict(color="#10b981", width=2.5),
                    marker=dict(size=5),
                )
                st.plotly_chart(format_plotly_fig(fig_daily), use_container_width=True)

            # ── Tab 2: Category Breakdown ────────────────────────────────
            with tab_cat:
                if "Transaction_Type" in df.columns:
                    expense_df = df[df["Transaction_Type"] == "EXPENSE"]
                elif "Direction" in df.columns:
                    expense_df = df[df["Direction"].str.upper().isin(["DR", "DEBIT"])]
                else:
                    expense_df = df

                if expense_df.empty:
                   # Fallback if binary classification isn't consistent
                   expense_df = df

                if not expense_df.empty and "Category" in expense_df.columns:
                    cat_data = (
                        expense_df.groupby("Category")["Amount"]
                        .sum()
                        .reset_index()
                        .sort_values("Amount", ascending=False)
                    )
                    fig_cat = px.pie(
                        cat_data,
                        names="Category",
                        values="Amount",
                        title="Spending by Category",
                        hole=0.4,
                        color_discrete_sequence=px.colors.qualitative.Set3,
                    )
                    st.plotly_chart(format_plotly_fig(fig_cat), use_container_width=True)
                else:
                    st.info("No spending data available for charting or categories missing.")

            # ── Tab 3: Transaction Data ──────────────────────────────────
            with tab_data:
                st.dataframe(df, use_container_width=True, height=420)

                # CSV Export
                csv_bytes = df.to_csv(index=False).encode("utf-8")
                st.download_button(
                    label="📥 Export to CSV",
                    data=csv_bytes,
                    file_name="transactions_export.csv",
                    mime="text/csv",
                )

            # ── AI Financial Advisor ─────────────────────────────────────
            st.divider()
            st.subheader("🤖 Smart Wealth Advisor")

            if "Gemini" in analysis_mode and not api_key:
                st.warning("⚠️ Please provide your Google Gemini API key in the sidebar.")
            elif "Langflow" in analysis_mode and not langflow_url:
                st.warning("⚠️ Please provide the Langflow API endpoint in the sidebar.")
            elif "Langflow" in analysis_mode and not langflow_key:
                st.warning("⚠️ Please provide your Langflow API Key in the sidebar.")
            else:
                advisor_col1, advisor_col2 = st.columns([4, 1])
                with advisor_col1:
                    user_query = st.text_input(
                        "Ask anything about your financial patterns",
                        placeholder="e.g., How much did I spend on food last month? or Suggest a savings plan.",
                        label_visibility="collapsed"
                    )
                with advisor_col2:
                    ask_btn = st.button("✨ Analyze", type="primary", use_container_width=True)

                if ask_btn:
                    if not user_query:
                        st.info("💡 Pro Tip: Ask about your monthly trends or specific categories.")
                    else:
                        with st.status("🛠️ AI Agent Processing...", expanded=True) as status:
                            try:
                                if "Gemini" in analysis_mode:
                                    status.write("🔍 Analyzing transaction clusters...")
                                    insight = get_llm_insights(df, api_key, user_query)
                                else:
                                    status.write("🔗 Connecting to Langflow Engine...")
                                    top_trans = (
                                        df.sort_values("Amount", ascending=False)
                                        .head(20)
                                        .to_string(index=False)
                                    )
                                    context = f"Latest stats: {stats}\nTop Txns:\n{top_trans}"
                                    insight = call_langflow_api(f"Question: {user_query}\nContext: {context}", langflow_url, api_key=langflow_key)
                                
                                status.update(label="✅ Analysis Complete!", state="complete")
                                render_ai_response(insight)
                            except Exception as e:
                                status.update(label="❌ Analysis Failed", state="error")
                                st.error(f"Error: {str(e)}")

    except Exception as e:
        st.error(f"❌ Error processing PDF: {str(e)}")
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

else:
    # ── Welcome / Landing ────────────────────────────────────────────────
    st.markdown("")
    wcol1, wcol2, wcol3 = st.columns([1, 2, 1])
    with wcol2:
        st.markdown(
            """
            ### 👋 Welcome!

            Upload a **UPI statement PDF** in the sidebar to get started.

            **How it works:**
            1. 📤 **Upload** — Drop your bank-generated UPI PDF.
            2. 📊 **Analyze** — Instant charts, categories & stats.
            3. 🤖 **Ask AI** — Get personalized financial advice.
            """
        )

# ── Footer ───────────────────────────────────────────────────────────────────
render_footer()
