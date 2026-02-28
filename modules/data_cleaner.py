import pandas as pd
import re

def clean_data(raw_transactions):
    """
    Takes a list of raw transaction dictionaries and returns a clean DataFrame.
    """
    if not raw_transactions:
        return pd.DataFrame(columns=['Date', 'Time', 'Amount', 'Direction', 'Description', 'Category'])

    df = pd.DataFrame(raw_transactions)
    
    # Normalize column names
    # Map input headers to standard headers
    # Expected: Date, Time, Amount, Direction, Counterparty, Description...
    # We want: Date, Time, Amount, Receiver, Description, Category
    
    # Lowercase all columns for easier matching
    df.columns = [c.lower() for c in df.columns]
    
    # Date & Time
    if 'date' in df.columns:
        df['Date'] = pd.to_datetime(df['date'], dayfirst=True, errors='coerce')
    
    # Amount
    if 'amount' in df.columns:
        # Remove currency symbols and commas
        df['Amount'] = df['amount'].astype(str).apply(lambda x: re.sub(r'[^\d.]', '', x))
        df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce').fillna(0.0)
        
    # Standardize other columns
    rename_map = {
        'direction': 'Direction',
        'counterparty': 'Receiver',
        'description': 'Description',
        'category': 'Category' # Might be empty relying on LLM later
    }
    
    for old, new in rename_map.items():
        if old in df.columns:
            df.rename(columns={old: new}, inplace=True)
            
    # If Category is missing, add it
    if 'Category' not in df.columns:
        df['Category'] = 'Uncategorized'
        
    # Return desired columns
    required_cols = ['Date', 'Time', 'Amount', 'Direction', 'Receiver', 'Description', 'Category']
    # Filter only existing
    final_cols = [c for c in required_cols if c in df.columns]
    
    return df[final_cols]
