@echo off
echo ============================================
echo   Mouse Recorder - Build EXE
echo ============================================
echo.

REM Clean previous build
if exist "dist" rmdir /s /q "dist"
if exist "build" rmdir /s /q "build"

echo [1/3] Installing dependencies...
python -m pip install pynput pyinstaller -q

echo [2/3] Building EXE...
python -m PyInstaller MouseRecorder.spec --clean --noconfirm

echo.
if exist "dist\MouseRecorder\MouseRecorder.exe" (
    echo [3/3] Build successful!
    echo   Output: dist\MouseRecorder\MouseRecorder.exe
) else (
    echo [ERROR] Build failed!
    exit /b 1
)

echo.
echo Done!
pause
