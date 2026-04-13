@echo off
setlocal
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
cd /d "%~dp0"

:: --- UAC elevation: relaunch as admin if not already -----------------------
net session >nul 2>nul
if %errorlevel% neq 0 (
    echo Requesting administrator privileges...
    powershell -NoProfile -Command "Start-Process -FilePath 'cmd.exe' -ArgumentList ('/d /c \"' + '%~f0' + '\"') -Verb RunAs"
    exit /b
)

echo =============================================
echo  Screenshot Sentinel (Administrator)
echo =============================================
echo.

:: Step 1: Kill all leftover Python processes
echo [1/3] Killing old processes...
taskkill /f /im python.exe   >nul 2>nul
taskkill /f /im pythonw.exe  >nul 2>nul
powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object {$_.Name -eq 'node.exe' -and $_.CommandLine -like '*media-bridge*'} | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }" >nul 2>nul
timeout /t 2 /nobreak >nul
echo     done

:: Step 2: Find Python (prefer py launcher, avoid MS Store stub)
echo [2/3] Finding Python...
set PYTHON_EXE=

where py >nul 2>nul
if %errorlevel%==0 (
    py --version >nul 2>nul
    if %errorlevel%==0 set PYTHON_EXE=py
)

if "%PYTHON_EXE%"=="" if exist "C:\Program Files\Python311\python.exe" (
    set "PYTHON_EXE=C:\Program Files\Python311\python.exe"
)
if "%PYTHON_EXE%"=="" if exist "C:\Users\86133\AppData\Local\Programs\Python\Python311\python.exe" (
    set "PYTHON_EXE=C:\Users\86133\AppData\Local\Programs\Python\Python311\python.exe"
)

if "%PYTHON_EXE%"=="" goto :nopython
echo     found: %PYTHON_EXE%

:: Step 3: Check / install dependencies
echo [3/3] Checking dependencies...
"%PYTHON_EXE%" -c "import pynput, PIL, pyperclip" >nul 2>nul
if %errorlevel% neq 0 (
    echo     Installing...
    "%PYTHON_EXE%" -m pip install -r "%~dp0requirements.txt" --quiet
    if %errorlevel% neq 0 (
        echo.
        echo [ERROR] pip install failed. Run manually:
        echo   pip install -r requirements.txt
        goto :end
    )
)
echo     ok
echo.

:: Run
echo =============================================
echo  Ctrl+Shift+A  ->  Feishu screenshot (clipboard = image)
echo  Ctrl+Shift+X  ->  AI screenshot    (clipboard = path)
echo  Stop: Ctrl+C or close this window
echo =============================================
echo.
"%PYTHON_EXE%" "%~dp0feishu_screenshot_guard.py"
echo.
echo [Script exited]
goto :end

:nopython
echo.
echo [ERROR] Python not found!
echo  Install Python 3.11 from https://www.python.org/downloads/
echo  Check "Add Python to PATH" and "Install py launcher" during setup.

:end
echo.
pause
