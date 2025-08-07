@echo off
SETLOCAL

REM === Настройка ===
SET PYTHON_EXE=python
SET VENV_DIR=.venv
SET SCRIPT_NAME=ModsUpdate.py

REM === Проверка Python ===
%PYTHON_EXE% --version >nul 2>&1
IF ERRORLEVEL 1 (
    echo Python not found. Install Python and add it to path.
    pause
    exit /b
)

REM === Создание виртуального окружения ===
IF NOT EXIST %VENV_DIR% (
    echo Creating virtual env...
    %PYTHON_EXE% -m venv %VENV_DIR%
)

REM === Активация виртуального окружения ===
CALL %VENV_DIR%\Scripts\activate

REM === Обновление pip ===
echo Updating pip...
python -m pip install --upgrade pip

REM === Установка зависимостей ===
echo Installing dependencies...
pip install selenium webdriver-manager

REM === Запуск скрипта ===
echo Execution %SCRIPT_NAME%...
python %SCRIPT_NAME%

pause
ENDLOCAL
