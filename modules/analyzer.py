import pandas as pd
try:
    from langchain_google_genai import ChatGoogleGenerativeAI
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_core.output_parsers import StrOutputParser
except ImportError:
    pass # Handle gracefully if not installed, though requirements said so.

def calculate_stats(df):
    """
    Calculates basic statistics from the transactions DataFrame.
    """
    if df.empty:
        return {}
        
    total_spend = df[df['Direction'].str.upper().isin(['DR', 'DEBIT'])]['Amount'].sum()
    total_income = df[df['Direction'].str.upper().isin(['CR', 'CREDIT'])]['Amount'].sum()
    
    # Monthly breakdown
    df['Month'] = df['Date'].dt.to_period('M')
    monthly = df[df['Direction'].str.upper().isin(['DR', 'DEBIT'])].groupby('Month')['Amount'].sum().to_dict()
    # Convert Period to string
    monthly = {str(k): v for k, v in monthly.items()}
    
    return {
        'total_spend': total_spend,
        'total_income': total_income,
        'monthly_spending': monthly,
        'transaction_count': len(df)
    }

def get_llm_insights(df, api_key, prompt_text="Analyze my spending patterns."):
    """
    Uses Google Gemini via LangChain to analyze the transaction data.
    Implements a structured analysis prompt for budget planning and advice.
    """
    if not api_key:
        return "Please provide a Google Gemini API Key to use AI features."
        
    # Prepare data summary
    top_transactions = df.sort_values(by='Amount', ascending=False).head(30).to_string(index=False)
    stats = calculate_stats(df)
    
    # Wasteful detection summary
    wasteful = df[df['Category'] == 'Wasteful Expenses']
    wasteful_total = wasteful['Amount'].sum() if not wasteful.empty else 0
    wasteful_count = len(wasteful)

    context = f"""
    FINANCIAL SUMMARY:
    - Total Spent: {stats.get('total_spend')}
    - Total Income: {stats.get('total_income')}
    - Transaction Count: {stats.get('transaction_count')}
    
    WASTEFAL SPENDING DETECTION:
    - Total Wasteful: {wasteful_total} ({wasteful_count} transactions)
    - Examples: {wasteful['Description'].head(5).tolist() if not wasteful.empty else 'None'}

    MONTHLY TRENDS:
    {stats.get('monthly_spending')}
    
    TOP 30 DEBIT TRANSACTIONS:
    {top_transactions}
    """
    
    try:
        llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", google_api_key=api_key)
        
        template = ChatPromptTemplate.from_template(
            """
            You are a Personal Finance AI Advisor designed to help users optimize their spending.
            
            USER DATA CONTEXT:
            {context}

            USER REQUEST/QUESTION:
            {request}

            YOUR TASK:
            1. Provide a concise summary of the financial health based on the data.
            2. Identify specific 'wasteful' or 'unnecessary' spending patterns.
            3. Recommend 3 actionable steps to reduce spending or increase savings.
            4. If the user asked a specific question, answer it thoroughly.
            
            FORMATTING RULES:
            - Use high-quality Markdown.
            - Use tables or bullet points for clarity.
            - Keep the tone professional, encouraging, and premium.
            - Highlight critical alerts (e.g., high debt/low income ratio) using ⚠️.

            ADVICE:
            """
        )
        
        chain = template | llm | StrOutputParser()
        response = chain.invoke({"context": context, "request": prompt_text})
        return response
        
    except Exception as e:
        return f"Error communicating with AI: {str(e)}"

import requests

def call_langflow_api(message, endpoint, tweaks=None, api_key=None):
    """
    Calls a Langflow API endpoint with advanced result extraction.
    """
    # Simple Tweak example from the Langflow image logic
    default_tweaks = {}
    
    current_tweaks = tweaks if tweaks else default_tweaks
    
    payload = {
        "input_value": message,
        "output_type": "chat",
        "input_type": "chat",
        "tweaks": current_tweaks
    }
        
    try:
        headers = {}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
            headers["x-api-key"] = api_key
            
        response = requests.post(endpoint, json=payload, headers=headers, timeout=30)
        
        # Check if the server returned HTML (often happens if flow_id is invalid and React catches it)
        content_type = response.headers.get('Content-Type', '')
        if 'text/html' in content_type:
             return f"⚠️ Langflow Error: The endpoint URL is invalid or the Flow ID does not exist. (Server returned HTML instead of JSON)."
             
        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError as http_err:
            error_msg = f"Langflow API Error (HTTP {response.status_code}): {response.text}"
            return error_msg
            
        result = response.json()
        
        # Robustly extract text from various Langflow output structures
        try:
            # 1. Direct result path
            if "outputs" in result:
                outputs = result["outputs"]
                if outputs and "outputs" in outputs[0]:
                    messages = outputs[0]["outputs"]
                    if messages and "results" in messages[0]:
                        msg_data = messages[0]["results"].get("message", {})
                        if "text" in msg_data:
                            return msg_data["text"]
                        
            # 2. Alternative result path
            if "outputs" in result:
                for out in result["outputs"]:
                    if "results" in out and "message" in out["results"]:
                        return out["results"]["message"].get("text", str(result))

            # 3. Recursive search fallback
            def find_text_node(obj):
                if isinstance(obj, dict):
                    if "text" in obj and isinstance(obj["text"], str) and len(obj["text"]) > 10:
                        return obj["text"]
                    for k, v in obj.items():
                        res = find_text_node(v)
                        if res: return res
                elif isinstance(obj, list):
                    for item in obj:
                        res = find_text_node(item)
                        if res: return res
                return None

            extracted = find_text_node(result)
            return extracted if extracted else f"Successfully called Langflow, but couldn't parse text. RAW: {str(result)[:500]}..."

        except Exception as parse_err:
            return f"Parsing Result Error: {parse_err}. RAW: {str(result)[:200]}"

    except Exception as e:
        return f"Langflow Request Failed: {str(e)}"
