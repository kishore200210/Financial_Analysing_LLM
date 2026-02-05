@echo off
echo Installing dependencies...
pip install -r requirements.txt
if %ERRORLEVEL% NEQ 0 (
    echo Error installing dependencies. Please check your Python installation.
    pause
    exit /b %ERRORLEVEL%
)

echo Starting Financial Analyzer AI...
streamlit run src/app.py
pause
