import re
import pdfplumber

def parse_pdf(file_path):
    """
    Parses a UPI transaction PDF using regex on extracted text.
    """
    transactions = []
    
    # Regex to capture: Date Time Amount ...
    # Example: 31-07-2025 10:46 17784 ...
    # Adjust regex based on observation:
    # Date: \d{2}-\d{2}-\d{4}
    # Time: \d{2}:\d{2}
    # Amount: [\d\.,]+ (digits, dots, commas)
    # The rest is harder to split without clear delimiters, but let's try to capture the line.
    
    line_pattern = re.compile(r'(\d{2}-\d{2}-\d{4})\s+(\d{2}:\d{2})\s+([\d\.,]+)\s+(.*)')
    
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if not text:
                continue
                
            for line in text.split('\n'):
                match = line_pattern.search(line)
                if match:
                    date, time, amount, rest = match.groups()
                    
                    # 'rest' contains Direction, Counterparty, Description, Category run together.
                    # We might need heuristics to split them. 
                    # For now, let's put 'rest' into Description and let Data Cleaner/LLM handle it
                    # OR try to split if we see common keywords like "DR", "CR".
                    
                    # Heuristic: Direction (DR/CR) usually follows amount? 
                    # If 'rest' starts with DR or CR.
                    
                    direction = "Unknown"
                    receiver = "Unknown"
                    desc = rest
                    
                    # Simple split attempt
                    parts = rest.split()
                    if parts:
                        if parts[0].upper() in ['DR', 'CR', 'DEBIT', 'CREDIT']:
                            direction = parts[0]
                            desc = " ".join(parts[1:])
                    
                    record = {
                        'date': date,
                        'time': time,
                        'amount': amount,
                        'direction': direction,
                        'counterparty': receiver, # Hard to isolate without more structure
                        'description': desc
                    }
                    transactions.append(record)
                            
    return transactions
