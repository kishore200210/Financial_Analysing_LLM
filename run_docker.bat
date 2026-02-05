@echo off
echo Stopping any running containers...
docker-compose down

echo Building and starting Langflow and Streamlit in Docker...
docker-compose up --build -d

echo.
echo Services are starting...
echo Langflow Dashboard will be available at: http://localhost:7860
echo Financial Analyzer UI will be available at: http://localhost:8501
echo.
echo To stop services, run: docker-compose down
pause
