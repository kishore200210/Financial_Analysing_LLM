from src.modules.pdf_parser import parse_pdf
from src.modules.data_cleaner import clean_data
import pandas as pd

try:
    print("Parsing PDF...")
    raw = parse_pdf("personal_financial_transcactions.pdf")
    print(f"Extracted {len(raw)} transactions.")
    
    if len(raw) > 0:
        print("First raw transaction:", raw[0])
        
    print("Cleaning data...")
    df = clean_data(raw)
    print("DataFrame shape:", df.shape)
    print("Columns:", df.columns.tolist())
    print("First 5 rows:")
    print(df.head())
    
    # Check if we have data
    if not df.empty:
        print("SUCCESS: Data extracted and cleaned.")
    else:
        print("WARNING: DataFrame is empty.")
        
except Exception as e:
    print(f"ERROR: {e}")
