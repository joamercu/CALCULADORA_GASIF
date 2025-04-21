@echo off
cd /d %~dp0
call .venv\Scripts\activate
streamlit run app_streamlit.py
pause
