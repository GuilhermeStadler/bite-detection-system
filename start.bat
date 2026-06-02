@echo off
cd /d "%~dp0"

if not exist ".venv\Scripts\activate.bat" (
  call setup_env.bat
)

if not exist ".venv\Scripts\activate.bat" (
  echo Nao foi possivel preparar o ambiente virtual. Feche processos Python abertos e tente novamente.
  pause
  exit /b 1
)

call .venv\Scripts\activate.bat
python -m pip install -r requirements.txt
python app.py
