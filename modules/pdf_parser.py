import re
import pdfplumber

def parse_pdf(file_path):
    """
    Parses a UPI statement PDF using pdfplumber's table extraction and regex fallback.
    Supports Paytm, PhonePe, and GPay formats.
    """
    transactions = []
    
    # Common Patterns for varied layouts
    # 1. DD-MM-YYYY HH:MM Amount Counterparty/Description
    p1 = re.compile(r'(\d{2}-\d{2}-\d{4})\s+(\d{2}:\d{2})\s+([\d\.,]+)\s+(.*)')
    # 2. DD/MM/YY Amount Counterparty
    p2 = re.compile(r'(\d{2}/\d{2}/\d{2,4})\s+([\d\.,]+)\s+(.*)')
    # 3. MMM DD, YYYY Amount (GPay style)
    p3 = re.compile(r'([a-zA-Z]{3}\s+\d{1,2},\s+\d{4})\s+([\d\.,]+)\s+(.*)')

    try:
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                # Attempt table extraction first for structured layouts (PhonePe/Paytm)
                tables = page.extract_tables()
                if tables:
                    for table in tables:
                        for row in table:
                            # Heuristic: Row must have at least 3 columns and look like a transaction
                            if row and len(row) >= 3:
                                clean_row = [str(cell).strip() for cell in row if cell]
                                if any(re.search(r'\d{2}[-/]\d{2}[-/]', s) for s in clean_row):
                                    # Very basic heuristic for mapping - needs refinement per app
                                    transactions.append({
                                        'raw': " | ".join(clean_row),
                                        'source': 'table'
                                    })
                
                # Regex fallback for unstructured text (GPay/Notifications)
                text = page.extract_text()
                if not text: continue
                
                for line in text.split('\n'):
                    line = line.strip()
                    if not line: continue
                    
                    found = False
                    for p in [p1, p2, p3]:
                        match = p.search(line)
                        if match:
                            groups = match.groups()
                            if len(groups) == 4:
                                transactions.append(format_record(groups[0], groups[1], groups[2], groups[3]))
                            else:
                                transactions.append(format_record(groups[0], "00:00", groups[1], groups[2]))
                            found = True
                            break
                    
                    if not found and " | " in line: # Potentially from table above
                        # Try to format raw table row if possible
                        pass

    except Exception as e:
        print(f"Parsing error: {e}")
                
    return transactions

def format_record(date, time, amount, rest):
    direction = "Unknown"
    desc = rest
    
    # Heuristic for direction
    upper_rest = rest.upper()
    # Expenses: Paid, Sent, Debited, (-)
    if any(x in upper_rest for x in ['DR', 'DEBIT', 'PAID TO', 'SENT TO', 'PURCHASE', 'TRANSFER TO']):
        direction = "DR"
    # Income: Received, Credited, (+), Refund
    elif any(x in upper_rest for x in ['CR', 'CREDIT', 'RECEIVED FROM', 'REFUND', 'CASHBACK', 'TRANSFER FROM']):
        direction = "CR"
        
    # Remove Direction marker from description if it's at the start/end
    parts = rest.split()
    if parts:
        if parts[0].upper() in ['DR', 'CR', 'DEBIT', 'CREDIT']:
            desc = " ".join(parts[1:])
        elif parts[-1].upper() in ['DR', 'CR', 'DEBIT', 'CREDIT']:
            desc = " ".join(parts[:-1])

    return {
        'date': date,
        'time': time,
        'amount': amount,
        'direction': direction,
        'counterparty': "Unknown",
        'description': desc
    }
