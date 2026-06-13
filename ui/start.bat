@echo off
echo ========================================================
echo   Starting Vision-RAG (Deep Space UI Edition)
echo ========================================================
echo.
echo Installing dependencies (this might take a minute)...
call npm install
echo.
echo Starting the web server...
call npm run dev
