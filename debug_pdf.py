import pdfplumber

with pdfplumber.open("personal_financial_transcactions.pdf") as pdf:
    print(f"Total Pages: {len(pdf.pages)}")
    for i, page in enumerate(pdf.pages):
        print(f"--- Page {i+1} ---")
        tables = page.extract_tables()
        print(f"Found {len(tables)} tables.")
        for table in tables:
            print("Table start:")
            for row in table[:3]:
                print(row)
        
        if not tables:
            print("No tables found. First 500 chars of text:")
            print(page.extract_text()[:500])
