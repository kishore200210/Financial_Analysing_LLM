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
    """
    if not api_key:
        return "Please provide a Google Gemini API Key to use AI features."
        
    # Prepare data summary for LLM to avoid token limits
    # We'll take the top 50 largest transactions and a monthly summary
    
    top_transactions = df.sort_values(by='Amount', ascending=False).head(50).to_string(index=False)
    stats = calculate_stats(df)
    
    context = f"""
    Here is a financial summary:
    Total Clean Spending: {stats.get('total_spend')}
    Total Income: {stats.get('total_income')}
    Monthly Breakdown: {stats.get('monthly_spending')}
    
    Top 50 Transactions:
    {top_transactions}
    """
    
    try:
        if "langflow" in api_key.lower() or api_key.startswith("http"):
            # Assume api_key is actually the Langflow Endpoint URL in this specific context override
            # Or better, let's keep api_key for Gemini and add a separate argument/logic.
            # For simplicity in this edit, I will add a check.
            pass

        llm = ChatGoogleGenerativeAI(model="gemini-pro", google_api_key=api_key)
        
        template = ChatPromptTemplate.from_template(
            """
            You are a helpful financial assistant. Analyze the following transaction data and answer the user's request.
            
            Context Data:
            {context}
            
            User Request:
            {request}
            
            Provide specific, actionable advice. Format as Markdown.
            """
        )
        
        chain = template | llm | StrOutputParser()
        response = chain.invoke({"context": context, "request": prompt_text})
        return response
        
    except Exception as e:
        return f"Error communicating with AI: {str(e)}"

import requests

def call_langflow_api(message, endpoint, tweaks=None):
    """
    Calls a Langflow API endpoint.
    """
    payload = {
        "input_value": message,
        "output_type": "chat",
        "input_type": "chat",
    }
    if tweaks:
        payload["tweaks"] = tweaks
        
    try:
        response = requests.post(endpoint, json=payload)
        response.raise_for_status()
        result = response.json()
        
        # Robustly extract the text result
        try:
            outputs = result.get("outputs", [])
            if outputs:
                # Direct message path (Modern Langflow)
                inner_outputs = outputs[0].get("outputs", [{}])
                results = inner_outputs[0].get("results", {})
                message = results.get("message", {})
                if "text" in message:
                    return message["text"]
                
                # Legacy path
                results_legacy = outputs[0].get("results", {})
                message_legacy = results_legacy.get("message", {})
                data = message_legacy.get("data", {})
                if "text" in data:
                    return data["text"]

            # Final Fallback: recursive search
            def find_text(d):
                if isinstance(d, dict):
                    if "text" in d and isinstance(d["text"], str): return d["text"]
                    for v in d.values():
                        res = find_text(v)
                        if res: return res
                elif isinstance(d, list):
                    for item in d:
                        res = find_text(item)
                        if res: return res
                return None
            
            extracted = find_text(result)
            return extracted if extracted else str(result)
            
        except (KeyError, IndexError, TypeError):
            return str(result)
    except Exception as e:
        return f"Langflow Error: {str(e)}"
