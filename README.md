# Financial Analyzer AI 💰

A Streamlit-based application that analyzes your personal financial transaction PDFs (UPI, Bank Statements) using AI to provide spending insights and visualizations.

## Features
- **PDF Parsing**: extract transactions from standard UPI PDFs (Paytm, PhonePe, GPay).
- **Interactive Dashboard**: View total spend, income, transaction types, and daily trends.
- **AI Insights**: Chat with your financial data using Google Gemini or a Langflow agent.
- **Visualizations**: Interactive charts for daily volume and category breakdowns.

## Project Structure
```
├── src/
│   ├── app.py              # Main Streamlit Application
│   └── modules/            # Helper modules
│       ├── pdf_parser.py   # PDF Extraction logic
│       ├── data_cleaner.py # Data transformation
│       └── analyzer.py     # Statistics & LLM integration
├── requirements.txt        # Python dependencies
├── Dockerfile              # Docker configuration
└── README.md               # This file
```

## Setup & Running

### Option 1: Run Locally
1.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```
2.  **Start the App**:
    ```bash
    streamlit run src/app.py
    ```
3.  **Open in Browser**:
    The app will open automatically at `http://localhost:8501`.

### Option 2: Run with Docker
1.  **Build**:
    ```bash
    docker build -t financial-ai .
    ```
2.  **Run**:
    ```bash
    docker run -p 8501:8501 financial-ai
    ```

## Usage
1.  **Upload PDF**: Upload your bank or UPI transaction PDF in the sidebar.
2.  **Enter API Key**:
    - Select "Internal AI (Gemini)" and enter your Google Gemini API Key.
    - Or select "Langflow API" and provide the endpoint URL.
3.  **Analyze**:
    - View the dashboard stats and charts.
    - Use the "AI Financial Advisor" section to ask questions like "Where do I spend the most money?" or "Analyze my weekend spending."

## Dependencies
- `streamlit`
- `pandas`
- `pdfplumber`
- `langchain-google-genai`
- `plotly`

#api key - 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