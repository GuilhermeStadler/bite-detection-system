@echo off
cd /d "%~dp0"

if not exist ".venv\Scripts\activate.bat" (
  call setup_env.bat
)

if not exist ".venv\Scripts\activate.bat" (
  echo Ambiente virtual nao encontrado. Rode setup_env.bat primeiro.
  pause
  exit /b 1
)

call .venv\Scripts\activate.bat
python -m pip install -r requirements-image.txt
python train_image_model.py
pause
