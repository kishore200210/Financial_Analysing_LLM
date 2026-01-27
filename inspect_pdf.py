import sys
try:
    import fitz  # PyMuPDF
    doc = fitz.open("personal_financial_transcactions.pdf")
    print("--- PAGE 1 ---")
    print(doc[0].get_text())
    print("--- PAGE 2 ---")
    if len(doc) > 1:
        print(doc[1].get_text())
except ImportError:
    print("PyMuPDF not installed, trying pdfplumber")
    try:
        import pdfplumber
        with pdfplumber.open("personal_financial_transcactions.pdf") as pdf:
            print("--- PAGE 1 ---")
            print(pdf.pages[0].extract_text())
    except ImportError:
        print("Neither PyMuPDF nor pdfplumber installed.")
