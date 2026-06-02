@echo off
cd /d "%~dp0"

set "PYTHON_CMD=python"
%PYTHON_CMD% --version >nul 2>nul
if errorlevel 1 (
  set "PYTHON_CMD=py -3"
  %PYTHON_CMD% --version >nul 2>nul
)

if errorlevel 1 (
  echo Python nao encontrado. Instale o Python e marque a opcao "Add python.exe to PATH".
  pause
  exit /b 1
)

if exist ".venv" (
  if not exist ".venv\pyvenv.cfg" (
    echo Ambiente .venv quebrado encontrado. Removendo para recriar...
    rmdir /s /q ".venv"
  )
)

if not exist ".venv\Scripts\activate.bat" (
  %PYTHON_CMD% -m venv .venv
)

if not exist ".venv\Scripts\activate.bat" (
  echo Nao foi possivel criar o ambiente virtual.
  pause
  exit /b 1
)

call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -r requirements-image.txt

echo.
echo Ambiente pronto.
pause
