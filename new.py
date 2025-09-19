# --- Imports ---
import os
import re
import base64
from io import BytesIO
from datetime import datetime

import streamlit as st
import pandas as pd
import pdfplumber
import plotly.express as px

from dotenv import load_dotenv

load_dotenv()  # load .env once
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# OpenAI import (single place)
try:
    import openai
except Exception:
    openai = None

# Read API key from .env
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if OPENAI_API_KEY and openai:
    openai.api_key = OPENAI_API_KEY

# ----------------------------
# Config (Streamlit)
# ----------------------------
st.set_page_config(page_title="Personal UPI Analyzer", layout="wide")

# Show API key status in sidebar
def openai_key_status_message():
    if not OPENAI_API_KEY:
        return ("No API key found", False)
    if not str(OPENAI_API_KEY).startswith("sk-"):
        return ("API key found but does not look valid (should start with 'sk-')", False)
    short = f"{OPENAI_API_KEY[:5]}...{OPENAI_API_KEY[-4:]}"
    if openai:
        try:
            resp = openai.Model.list()
            return (f"OpenAI key loaded ({short}). API test OK.", True)
        except Exception as e:
            return (f"OpenAI key loaded ({short}). API test FAILED: {e}", False)
    else:
        return (f"OpenAI key loaded ({short}) but openai package missing.", False)

msg, ok = openai_key_status_message()
if ok:
    st.sidebar.success(msg)
else:
    st.sidebar.warning(msg)



DATE_FORMATS = [
    "%d-%m-%Y %H:%M", "%d-%m-%Y %H:%M:%S", "%d-%m-%Y",
    "%Y-%m-%d %H:%M", "%Y-%m-%d", "%d/%m/%Y"
]

CATEGORY_KEYWORDS = {
    "Shopping": ["flipkart", "amazon", "myntra", "snapdeal"],
    "Food": ["zomato", "swiggy", "dominos", "pizza", "restaurant", "dine"],
    "Transport": ["ola", "uber", "rapido", "taxi"],
    "Bills": ["airtel", "bsnl", "tneb", "electricity", "bill", "vodafone"],
    "Rent": ["house owner", "flat rent", "rent"],
    "Salary": ["company", "salary", "payroll"],
    "Investment": ["sbi securities", "mutual fund", "sip", "investment"],
    "Entertainment": ["hotstar", "netflix", "bookmyshow"],
    "Groceries": ["bigbasket", "blinkit", "zepto"],
    "Transfer": ["self account", "friend transfer", "transfer"],
}

DIRECTION_DEBIT = {"debit", "dr", "withdrawal", "sent", "paid"}
DIRECTION_CREDIT = {"credit", "cr", "received", "deposit", "refund"}

# ----------------------------
# Parsing helpers
# ----------------------------
def clean_amount_str(s):
    if s is None:
        return None
    s = str(s).replace(",", "")
    m = re.search(r"-?\d+(\.\d+)?", s)
    return float(m.group(0)) if m else None

def guess_category(text):
    if not text or pd.isna(text):
        return "Unknown"
    t = str(text).lower()
    for cat, keywords in CATEGORY_KEYWORDS.items():
        if any(kw in t for kw in keywords):
            return cat
    if "salary" in t or "payroll" in t:
        return "Salary"
    if "transfer" in t:
        return "Transfer"
    return "Other"

def extract_text_from_pdf_bytes(bytes_data):
    texts = []
    try:
        with pdfplumber.open(BytesIO(bytes_data)) as pdf:
            for page in pdf.pages:
                txt = page.extract_text()
                if txt:
                    texts.append(txt)
    except Exception as e:
        st.warning(f"pdfplumber failed: {e}")
    return "\n".join(texts)

def parse_table_like_text(text):
    rows = []
    if not text:
        return pd.DataFrame()

    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        line_norm = re.sub(r"\s{2,}", "  ", line)

        # Pattern 1: standard format
        m = re.match(r"^(\d{1,2}[-/]\d{1,2}[-/]\d{4})\s+(\d{1,2}:\d{2})?\s+([-\d,\.]+)\s+([A-Za-z]+)\s+(.+)$", line_norm)
        if m:
            date_s, time_s, amount_s, direction, rest = m.groups()
            amt = clean_amount_str(amount_s)
            utr = None
            utr_m = re.search(r"(UTR[:\s]?[\w\d-]+)", rest, re.I)
            if utr_m:
                utr = utr_m.group(1)
                rest = rest.replace(utr, "").strip()
            parts = re.split(r"\bPayment related to\b|\bfor\b|\b-+\b", rest, flags=re.I)
            merchant = parts[0].strip() if parts else ""
            description = parts[1].strip() if len(parts) > 1 else rest.replace(merchant, "").strip()
            rows.append({
                "date": date_s, "time": time_s or "",
                "amount": amt, "direction": direction,
                "merchant": merchant, "description": description,
                "utr": utr
            })
            continue

        # Pattern 2: debit/credit with amount
        if re.search(r"\b(debit|credit|dr|cr)\b", line, re.I) and re.search(r"\d[\d,\.]+\b", line):
            amt = clean_amount_str(line)
            dir_m = re.search(r"\b(debit|credit|dr|cr|paid|sent|received|deposit)\b", line, re.I)
            direction = dir_m.group(1) if dir_m else ""
            date_m = re.search(r"(\d{1,2}[-/]\d{1,2}[-/]\d{4})", line)
            time_m = re.search(r"(\d{1,2}:\d{2})", line)
            rows.append({
                "date": date_m.group(0) if date_m else "",
                "time": time_m.group(0) if time_m else "",
                "amount": amt, "direction": direction,
                "merchant": line.split()[0], "description": line,
                "utr": None
            })
            continue

    return pd.DataFrame(rows)

def parse_pdf_to_df_from_bytes(bytes_data):
    text = extract_text_from_pdf_bytes(bytes_data)
    df = parse_table_like_text(text)
    if df.empty:
        return df

    df['amount'] = pd.to_numeric(df['amount'], errors='coerce').fillna(0.0)

    def parse_dt(row):
        s = f"{row.get('date','')} {row.get('time','')}".strip()
        for fmt in DATE_FORMATS:
            try:
                return datetime.strptime(s, fmt)
            except Exception:
                continue
        return pd.NaT

    df['datetime'] = df.apply(parse_dt, axis=1)
    for c in ['merchant','description','direction','utr']:
        if c in df.columns:
            df[c] = df[c].astype(str).str.strip().replace({'nan': ''})
    df['category'] = df.apply(lambda r: guess_category(" ".join([str(r.get('merchant','')), str(r.get('description','')), str(r.get('direction',''))])), axis=1)

    def signed_amount(r):
        d = str(r.get('direction','')).lower()
        amt = r.get('amount', 0.0) or 0.0
        if any(x in d for x in DIRECTION_DEBIT): return -abs(amt)
        if any(x in d for x in DIRECTION_CREDIT): return abs(amt)
        if "received" in str(r.get('description','')).lower() or "deposit" in str(r.get('description','')).lower():
            return abs(amt)
        return -abs(amt)

    df['amount_signed'] = df.apply(signed_amount, axis=1)

    final_cols = ['datetime','date','time','amount','amount_signed','direction','merchant','description','utr','category']
    for c in final_cols:
        if c not in df.columns: df[c] = ""
    return df[final_cols]

# ----------------------------
# LLM recommendations
# ----------------------------
def get_recommendations(transactions_df):
    if transactions_df.empty:
        return "No transactions available to analyze."

    total_spent = transactions_df[transactions_df['amount_signed'] < 0]['amount'].abs().sum()
    total_income = transactions_df[transactions_df['amount_signed'] > 0]['amount'].sum()
    top_categories = transactions_df.groupby('category')['amount_signed'].sum().abs().sort_values(ascending=False).head(5).to_dict()

    prompt = f"""
You are a helpful personal finance assistant.
Total income: {total_income:.2f}
Total spending: {total_spent:.2f}
Top categories: {top_categories}
Give me a spending summary, 5 recommendations, budget percentages, and suspicious activity if any.
"""

    if OPENAI_API_KEY and openai:
        try:
            resp = openai.ChatCompletion.create(
                model="gpt-4o-mini",
                messages=[{"role":"user","content":prompt}],
                max_tokens=500,
                temperature=0.2
            )
            return resp['choices'][0]['message']['content'].strip()
        except Exception as e:
            return f"LLM call failed: {e}"
    else:
        return (
            "LLM not configured. Suggestions:\n"
            "- Set up auto-save.\n"
            "- Cut down on entertainment by 10%.\n"
            "- Track grocery expenses weekly.\n"
            "- Review recurring bills.\n"
            "- Maintain emergency savings."
        )

# ----------------------------
# Streamlit UI
# ----------------------------
st.title("📊 Personal UPI Usage & Financial Analyzer")
st.markdown("Upload UPI PDF/CSV/TXT statements. The app will parse transactions and provide insights.")

uploaded = st.file_uploader("Upload files", type=['pdf','csv','txt'], accept_multiple_files=True)

@st.cache_data
def process_files_streamlit(files):
    dfs = []
    for f in files:
        try:
            content = f.read()
            name = f.name
            if name.lower().endswith(".pdf"):
                df = parse_pdf_to_df_from_bytes(content)
                if not df.empty:
                    df['source_file'] = name
                    dfs.append(df)
            elif name.lower().endswith(".csv"):
                df = pd.read_csv(BytesIO(content))
                df['source_file'] = name
                dfs.append(df)
            else:
                raw = content.decode(errors='ignore')
                df = parse_table_like_text(raw)
                if not df.empty:
                    df['source_file'] = name
                    dfs.append(df)
        except Exception as e:
            st.error(f"Failed to process {f.name}: {e}")
    return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()

if uploaded:
    df = process_files_streamlit(uploaded)
    if df.empty:
        st.error("No transactions parsed. Try different export format.")
    else:
        st.subheader("Parsed transactions (preview)")
        st.dataframe(df.head(200))

        st.subheader("Summary")
        total_income = df[df['amount_signed'] > 0]['amount'].sum()
        total_spent = df[df['amount_signed'] < 0]['amount'].abs().sum()
        col1, col2 = st.columns(2)
        col1.metric("Total Income", f"{total_income:.2f}")
        col2.metric("Total Spending", f"{total_spent:.2f}")

        st.subheader("Category Breakdown")
        cat = df.groupby('category')['amount'].sum().abs().reset_index()
        if not cat.empty:
            st.plotly_chart(px.pie(cat, names='category', values='amount'), use_container_width=True)

        st.subheader("Monthly Spending")
        df['datetime'] = pd.to_datetime(df['datetime'], errors='coerce')
        df['month'] = df['datetime'].dt.to_period("M").astype(str)
        monthly = df[df['amount_signed']<0].groupby('month')['amount_signed'].sum().abs().reset_index()
        if not monthly.empty:
            st.plotly_chart(px.bar(monthly, x='month', y='amount_signed'), use_container_width=True)

        st.subheader("Top Merchants")
        topm = df[df['amount_signed']<0].groupby('merchant')['amount_signed'].sum().abs().reset_index().nlargest(10,'amount_signed')
        st.table(topm)

        # Download CSV
        csv = df.to_csv(index=False).encode()
        b64 = base64.b64encode(csv).decode()
        st.markdown(f'<a href="data:file/csv;base64,{b64}" download="transactions.csv">Download CSV</a>', unsafe_allow_html=True)

        st.subheader("LLM Recommendations")
        if st.button("Get Recommendations"):
            rec = get_recommendations(df)
            st.write(rec)
else:
    st.info("Upload your UPI statements to begin.")
