"""
Transaction Classifier Module
Implements:
- Binary Classification (Spend vs Income)
- Multi-class categorization using Transformers (zero-shot)
- Text Pair Modeling for description-category matching
"""
import pandas as pd

try:
    from transformers import pipeline
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False

# Spending categories for classification
SPENDING_CATEGORIES = [
    "Food & Dining", "Transportation", "Shopping", "Entertainment",
    "Health & Fitness", "Bills & Utilities", "Rent & Housing", 
    "Travel", "Investment", "Salary & Income", "Wasteful Expenses", "Miscellaneous"
]

class TransactionClassifier:
    """
    Classifies UPI transactions using:
    1. Binary Classification: Spend (DR) vs Income (CR)
    2. Zero-shot classification for spending categories
    3. Rule-based fallback for speed
    """
    
    def __init__(self, use_ml=True):
        self.use_ml = use_ml and TRANSFORMERS_AVAILABLE
        self.classifier = None
        
        if self.use_ml:
            try:
                # Zero-shot classifier using BART/MNLI for text pair modeling
                self.classifier = pipeline(
                    "zero-shot-classification",
                    model="facebook/bart-large-mnli"
                )
            except Exception as e:
                print(f"ML model load failed: {e}. Using rule-based fallback.")
                self.use_ml = False

    def binary_classify(self, direction_str):
        """
        Binary Classification: Classifies transaction as EXPENSE or INCOME.
        """
        direction_str = str(direction_str).upper()
        if any(x in direction_str for x in ['DR', 'DEBIT', 'PAID', 'SENT', 'TRANSFER TO']):
            return "EXPENSE"
        elif any(x in direction_str for x in ['CR', 'CREDIT', 'RECEIVED', 'REFUND', 'CASHBACK', 'TRANSFER FROM']):
            return "INCOME"
        return "UNKNOWN"

    def categorize(self, description):
        """
        Multi-class categorization using zero-shot classification (Text Pair Modeling).
        Falls back to rule-based if ML is unavailable.
        """
        if self.use_ml and self.classifier:
            try:
                result = self.classifier(description, SPENDING_CATEGORIES)
                return result['labels'][0]
            except:
                return self._rule_based_categorize(description)
        return self._rule_based_categorize(description)

    def _rule_based_categorize(self, description):
        """Rule-based fallback for categorization."""
        desc_lower = description.lower()
        
        # Priority: Wasteful / Gambling / Unnecessary subscriptions
        if any(w in desc_lower for w in ['dream11', 'rummy', 'casino', 'betting', 'winzo', 'poker']):
            return "Wasteful Expenses"
        
        if any(w in desc_lower for w in ['swiggy', 'zomato', 'food', 'restaurant', 'cafe', 'pizza', 'kfc', 'mcdonald']):
            return "Food & Dining"
        if any(w in desc_lower for w in ['uber', 'ola', 'petrol', 'fuel', 'metro', 'bus', 'rapido', 'train']):
            return "Transportation"
        if any(w in desc_lower for w in ['amazon', 'flipkart', 'myntra', 'shopping', 'store', 'ajio', 'nykaa']):
            return "Shopping"
        if any(w in desc_lower for w in ['netflix', 'spotify', 'movie', 'hotstar', 'prime', 'game', 'pvr', 'inox']):
            return "Entertainment"
        if any(w in desc_lower for w in ['hospital', 'pharmacy', 'doctor', 'gym', 'health', 'apollo', 'cultfit']):
            return "Health & Fitness"
        if any(w in desc_lower for w in ['electricity', 'water', 'gas', 'bill', 'recharge', 'mobile', 'jio', 'airtel']):
            return "Bills & Utilities"
        if any(w in desc_lower for w in ['rent', 'landlord', 'owner', 'housing', 'maintenance', 'nobroker']):
            return "Rent & Housing"
        if any(w in desc_lower for w in ['hotel', 'flight', 'booking', 'travel', 'trip', 'makemytrip', 'agoda']):
            return "Travel"
        if any(w in desc_lower for w in ['mutual fund', 'stock', 'investment', 'sip', 'trading', 'groww', 'zerodha']):
            return "Investment"
        if any(w in desc_lower for w in ['salary', 'credited', 'income', 'payment received']):
            return "Salary & Income"
        
        return "Miscellaneous"

    def classify_dataframe(self, df):
        """
        Applies both binary and multi-class classification to a DataFrame.
        """
        if 'Direction' in df.columns:
            df['Transaction_Type'] = df['Direction'].apply(self.binary_classify)
        
        if 'Description' in df.columns:
            df['Category'] = df['Description'].apply(self.categorize)
        
        return df


# Test the classifier
if __name__ == "__main__":
    classifier = TransactionClassifier(use_ml=False)  # Use rule-based for quick test
    
    test_cases = [
        ("Paid to Swiggy for dinner", "DR"),
        ("Received from Employer Salary", "CR"),
        ("Uber ride to office", "DEBIT"),
        ("Amazon shopping order", "DR"),
        ("Netflix subscription", "DR"),
    ]
    
    print("=== Transaction Classifier Test ===")
    for desc, direction in test_cases:
        binary = classifier.binary_classify(direction)
        category = classifier.categorize(desc)
        print(f"  Desc: '{desc}' | Direction: {direction}")
        print(f"    -> Binary: {binary} | Category: {category}")
        print()
