

import os                # ✅ must come first
from dotenv import load_dotenv

# --- Load environment variables ---
load_dotenv()  # looks for .env in the same folder as app.py

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Optional: enable OpenAI LLM recommendations (set OPENAI_API_KEY as env var)
try:
    import openai
except Exception:
    openai = None

if OPENAI_API_KEY and openai:
    openai.api_key = OPENAI_API_KEY
    print("✅ OpenAI API key loaded successfully")
else:
    print("❌ No API key found! Please check your .env file")


import re
import os
import tempfile
from datetime import datetime
from io import BytesIO
import base64

import pandas as pd
import pdfplumber

import streamlit as st
import plotly.express as px

# Optional: enable OpenAI LLM recommendations (set OPENAI_API_KEY as env var)
try:
    import openai
except Exception:
    openai = None

# ----------------------------
# Config & helper data
# ----------------------------
st.set_page_config(page_title="Personal UPI Analyzer", layout="wide")

DATE_FORMATS = [
    "%d-%m-%Y %H:%M", "%d-%m-%Y %H:%M:%S", "%d-%m-%Y",
    "%Y-%m-%d %H:%M", "%Y-%m-%d", "%d/%m/%Y",
    "%d-%m-%Y %H:%M"
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
    s = str(s)
    # remove non-digit except dot and minus
    s = s.replace(",", "")
    m = re.search(r"-?\d+(\.\d+)?", s)
    return float(m.group(0)) if m else None

def guess_category(text):
    if not text or pd.isna(text):
        return "Unknown"
    t = str(text).lower()
    for cat, keywords in CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if kw in t:
                return cat
    if "salary" in t or "payroll" in t: return "Salary"
    if "transfer" in t: return "Transfer"
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
        # file might be corrupt or scanned image; return empty
        st.warning(f"pdfplumber failed to read PDF: {e}")
    return "\n".join(texts)

def parse_table_like_text(text):
    """
    Flexible parser: tries several patterns and fallback heuristics.
    Returns dataframe with columns: date,time,amount,direction,merchant,description,utr
    """
    rows = []
    if not text:
        return pd.DataFrame(rows)

    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue

        # normalize multiple spaces
        line_norm = re.sub(r"\s{2,}", "  ", line)

        # Pattern 1: dd-mm-yyyy [HH:MM] amount direction merchant ... (common)
        m = re.match(r"^(\d{1,2}[-/]\d{1,2}[-/]\d{4})\s+(\d{1,2}:\d{2})?\s+([-\d,\.]+)\s+([A-Za-z]+)\s+(.+)$", line_norm)
        if m:
            date_s, time_s, amount_s, direction, rest = m.groups()
            amt = clean_amount_str(amount_s)
            utr = None
            utr_m = re.search(r"(UTR[:\s]?[\w\d-]+)", rest, re.I)
            if utr_m:
                utr = utr_m.group(1)
                rest = rest.replace(utr, "").strip()
            # merchant heuristics: up to known keywords or 'Payment' words
            parts = re.split(r"\bPayment related to\b|\bfor\b|\b-+\b", rest, flags=re.I)
            merchant = parts[0].strip() if parts else ""
            description = parts[1].strip() if len(parts) > 1 else rest.replace(merchant, "").strip()
            rows.append({
                "date": date_s,
                "time": time_s if time_s else "",
                "amount": float(amt) if amt is not None else None,
                "direction": direction,
                "merchant": merchant,
                "description": description,
                "utr": utr
            })
            continue

        # Pattern 2: lines with 'debit'/'credit' anywhere and amount nearby
        if re.search(r"\b(debit|credit|dr|cr)\b", line, re.I) and re.search(r"\d[\d,\.]+\b", line):
            amt = clean_amount_str(line)
            dir_m = re.search(r"\b(debit|credit|dr|cr|paid|sent|received|deposit)\b", line, re.I)
            direction = dir_m.group(1) if dir_m else ""
            # attempt to extract date from line
            date_m = re.search(r"(\d{1,2}[-/]\d{1,2}[-/]\d{4})", line)
            time_m = re.search(r"(\d{1,2}:\d{2})", line)
            rest = line
            if date_m:
                rest = rest.replace(date_m.group(0), "")
            if time_m:
                rest = rest.replace(time_m.group(0), "")
            # best-effort merchant = first word chunk
            merchant = rest.split()[0] if rest.split() else ""
            description = rest.strip()
            rows.append({
                "date": date_m.group(0) if date_m else "",
                "time": time_m.group(0) if time_m else "",
                "amount": float(amt) if amt is not None else None,
                "direction": direction,
                "merchant": merchant,
                "description": description,
                "utr": None
            })
            continue

        # Fallback: try splitting by two or more spaces (table-like)
        toks = re.split(r"\s{2,}", line)
        if len(toks) >= 4:
            amt = clean_amount_str(toks[2])
            rows.append({
                "date": toks[0],
                "time": toks[1] if len(toks) > 1 else "",
                "amount": float(amt) if amt is not None else None,
                "direction": toks[3] if len(toks) > 3 else "",
                "merchant": toks[4] if len(toks) > 4 else "",
                "description": " ".join(toks[5:]) if len(toks) > 5 else ""
            })
            continue

        # otherwise: ignore noisy line
        continue

    df = pd.DataFrame(rows)
    return df

# ----------------------------
# Master parse + normalization
# ----------------------------
def parse_pdf_to_df_from_bytes(bytes_data):
    text = extract_text_from_pdf_bytes(bytes_data)
    df = parse_table_like_text(text)
    if df.empty:
        return df

    # standardize columns
    if 'amount' in df.columns:
        df['amount'] = pd.to_numeric(df['amount'], errors='coerce').fillna(0.0)
    else:
        df['amount'] = 0.0

    # combine date+time -> datetime
    def parse_dt(row):
        s = f"{row.get('date','')} {row.get('time','')}".strip()
        for fmt in DATE_FORMATS:
            try:
                return datetime.strptime(s, fmt)
            except Exception:
                continue
        # fallback: try date only heuristics
        for fmt in ["%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d"]:
            try:
                return datetime.strptime(row.get('date','') or '', fmt)
            except Exception:
                continue
        return pd.NaT

    df['datetime'] = df.apply(parse_dt, axis=1)

    # strip/normalize merchant & description
    for c in ['merchant','description','direction','utr']:
        if c in df.columns:
            df[c] = df[c].astype(str).str.strip().replace({'nan': ''})

    # category
    df['category'] = df.apply(lambda r: guess_category(" ".join([str(r.get('merchant','')), str(r.get('description','')), str(r.get('direction',''))])), axis=1)

    # amount_signed: debits negative
    def signed_amount(r):
        d = str(r.get('direction','')).lower()
        amt = r.get('amount', 0.0) or 0.0
        if any(x in d for x in DIRECTION_DEBIT):
            return -abs(amt)
        if any(x in d for x in DIRECTION_CREDIT):
            return abs(amt)
        # fallback heuristics using keywords in description
        desc = str(r.get('description','')).lower()
        if "received" in desc or "deposit" in desc:
            return abs(amt)
        return -abs(amt)  # assume spending if unclear

    df['amount_signed'] = df.apply(signed_amount, axis=1)

    # ensure final columns order
    final_cols = ['datetime','date','time','amount','amount_signed','direction','merchant','description','utr','category']
    for c in final_cols:
        if c not in df.columns:
            df[c] = ""
    df = df[final_cols]
    return df

# ----------------------------
# LLM recommendations helper
# ----------------------------
#api vaiable value
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if OPENAI_API_KEY and openai:
    openai.api_key = OPENAI_API_KEY;
    print("API key found", OPENAI_API_KEY)
else:
    print("❌ No API key found! Did you set .env correctly?")


def get_recommendations(transactions_df):
    # fallback: if no valid rows, return helpful message
    if transactions_df.empty:
        return "No transactions available to analyze."

    total_spent = transactions_df[transactions_df['amount_signed'] < 0]['amount'].abs().sum()
    total_income = transactions_df[transactions_df['amount_signed'] > 0]['amount'].sum()
    top_categories = transactions_df.groupby('category')['amount_signed'].sum().abs().sort_values(ascending=False).head(5).to_dict()
    recent = transactions_df.sort_values('datetime', ascending=False).head(10)[['datetime','merchant','amount_signed','category']].to_dict(orient='records')

    prompt = f"""
You are a helpful personal finance assistant. Summarize this user's spending data and give actionable recommendations.
Total income: {total_income:.2f}
Total spending: {total_spent:.2f}
Top categories: {top_categories}
Recent transactions: {recent}

Provide:
1) One-paragraph summary of spending behaviour.
2) Five actionable recommendations to reduce unnecessary expenses & improve savings.
3) Suggested monthly budget percentages by category.
4) Anything suspicious to review.
Respond concisely.
"""


    if OPENAI_API_KEY and openai:
        try:
            # use ChatCompletion if available; otherwise fallback
            resp = openai.ChatCompletion.create(
                model="gpt-4o-mini",
                messages=[{"role":"user","content":prompt}],
                max_tokens=600,
                temperature=0.2
            )
            return resp['choices'][0]['message']['content'].strip()
        except Exception as e:
            return f"LLM call failed: {e}\n\nPrompt used:\n{prompt}"
    else:
        # simple rule-based fallback
        recs = [
            "No OpenAI key set — set OPENAI_API_KEY env var for LLM suggestions.",
            "Reduce discretionary category by 10-20% next month.",
            "Set up auto-save: move fixed % of income to savings on payday.",
            "Review / cancel unused subscriptions in Entertainment.",
            "Compare grocery bills weekly & set a target."
        ]
        return "LLM not configured. Suggestions:\n" + "\n".join(f"- {r}" for r in recs)

# ----------------------------
# Streamlit UI
# ----------------------------
st.title("Personal UPI Usage & Financial Analyzer")
st.markdown("Upload UPI PDF statement(s) (or text/CSV). The app will try to parse transactions and provide insights.")

uploaded = st.file_uploader("Upload one or more PDF / CSV / TXT files", type=['pdf','csv','txt'], accept_multiple_files=True)

@st.cache_data
def process_files_streamlit(files):
    dfs = []
    for f in files:
        try:
            content = f.read()
            name = f.name
            if name.lower().endswith(".pdf") or getattr(f, "type", "") == "application/pdf":
                df = parse_pdf_to_df_from_bytes(content)
                if not df.empty:
                    df['source_file'] = name
                    dfs.append(df)
            elif name.lower().endswith(".csv") or getattr(f, "type","").startswith("text/csv"):
                try:
                    df = pd.read_csv(BytesIO(content))
                    dfs.append(df)
                except Exception as e:
                    st.warning(f"CSV read failed for {name}: {e}")
            else:
                # txt fallback
                try:
                    raw = content.decode(errors='ignore')
                except Exception:
                    raw = str(content)
                df = parse_table_like_text(raw)
                if not df.empty:
                    df['source_file'] = name
                    dfs.append(df)
        except Exception as e:
            st.error(f"Failed to process {f.name}: {e}")
    if dfs:
        out = pd.concat(dfs, ignore_index=True, sort=False)
        return out
    else:
        return pd.DataFrame()

if uploaded:
    with st.spinner("Parsing uploaded file(s)..."):
        df = process_files_streamlit(uploaded)
    if df.empty:
        st.error("Parsing produced no transactions. Try different statement export (CSV or text) or check sample format.")
    else:
        st.subheader("Parsed transactions (preview)")
        st.dataframe(df.head(200))

        # Summary metrics
        st.subheader("Summary")
        total_income = df[df['amount_signed'] > 0]['amount'].sum()
        total_spent = df[df['amount_signed'] < 0]['amount'].abs().sum()
        col1, col2 = st.columns(2)
        col1.metric("Total Income (sum credits)", f"{total_income:.2f}")
        col2.metric("Total Spending (sum debits)", f"{total_spent:.2f}")

        # Category breakdown (pie)
        st.subheader("Category breakdown")
        cat = df.groupby('category')['amount'].sum().abs().reset_index().sort_values(by='amount', ascending=False)
        if not cat.empty:
            fig = px.pie(cat, names='category', values='amount', title="Spending by category")
            st.plotly_chart(fig, use_container_width=True)

        # Monthly timeseries
        st.subheader("Spending over time")
        df_ts = df.copy()
        # make sure datetime column is proper
        df_ts['datetime'] = pd.to_datetime(df_ts['datetime'], errors='coerce')
        df_ts['month'] = df_ts['datetime'].dt.to_period("M").astype(str)
        monthly = df_ts[df_ts['amount_signed']<0].groupby('month')['amount_signed'].sum().abs().reset_index().sort_values('month')
        if not monthly.empty:
            fig2 = px.bar(monthly, x='month', y='amount_signed', labels={'amount_signed':'amount'}, title="Monthly spending")
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("No monthly spending data to show (datetime parsing may have failed).")

        # Top merchants
        st.subheader("Top merchants (by spend)")
        topm = df[df['amount_signed']<0].groupby('merchant')['amount_signed'].sum().abs().reset_index().sort_values(by='amount_signed', ascending=False).head(10)
        if not topm.empty:
            st.table(topm)
        else:
            st.info("No merchant spend data found.")

        # Download parsed CSV
        csv = df.to_csv(index=False).encode()
        b64 = base64.b64encode(csv).decode()
        href = f'<a href="data:file/csv;base64,{b64}" download="transactions_parsed.csv">Download parsed CSV</a>'
        st.markdown(href, unsafe_allow_html=True)

        # Filters
        st.subheader("Filter transactions")
        c1, c2 = st.columns([2,1])
        with c1:
            merchant_filter = st.text_input("Merchant contains")
        with c2:
            cat_options = ["All"] + sorted(df['category'].dropna().unique().tolist())
            cat_filter = st.selectbox("Category", options=cat_options)
        filtered = df.copy()
        if merchant_filter:
            filtered = filtered[filtered['merchant'].str.contains(merchant_filter, case=False, na=False)]
        if cat_filter and cat_filter != "All":
            filtered = filtered[filtered['category'] == cat_filter]
        st.dataframe(filtered.head(200))

        # LLM Recommendations
        st.subheader("Personalized recommendations (LLM)")
        if st.button("Get LLM Recommendations"):
            with st.spinner("Generating recommendations..."):
                rec = get_recommendations(df)
                st.markdown("**LLM Recommendations**")
                st.write(rec)
else:
    st.info("Upload your PDF statement(s) or a CSV/text export. Example row format:\n\n`02-09-2024 19:02 17734 debit Flipkart Payment related to Flipkart UTR100000 Shopping`")

# ----------------------------
# End
# ----------------------------
