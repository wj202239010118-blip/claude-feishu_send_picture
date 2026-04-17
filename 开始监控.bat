@echo off
setlocal EnableExtensions
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
cd /d "%~dp0"

set "PYEXE="
set "PYARGS="

where py >nul 2>nul
if %errorlevel%==0 (
  set "PYEXE=py"
  set "PYARGS=-3"
  goto py_ok
)

where python >nul 2>nul
if %errorlevel%==0 (
  set "PYEXE=python"
  goto py_ok
)

echo Python not found.
echo Install Python 3.9+ and enable: "Add Python to PATH".
echo.
goto done

:py_ok
echo =============================================
echo  Feishu Screenshot Sentinel
echo  Step 1: Ctrl+Shift+X  activate listener
echo  Step 2: Ctrl+Shift+A  take screenshot in Feishu
echo  Path auto-copied to clipboard for Claude
echo  Stop: Ctrl+C or close this window
echo =============================================
echo.

"%PYEXE%" %PYARGS% -c "import pynput, PIL, pyperclip" >nul 2>nul
if errorlevel 1 (
  echo Installing dependencies...
  "%PYEXE%" %PYARGS% -m pip install -r "%~dp0requirements.txt"
  echo.
  if errorlevel 1 (
    echo Install failed. Run manually:
    echo   pip install -r requirements.txt
    goto done
  )
)

"%PYEXE%" %PYARGS% "%~dp0feishu_screenshot_guard.py"
echo.
echo [Script exited]

:done
echo.
pause
