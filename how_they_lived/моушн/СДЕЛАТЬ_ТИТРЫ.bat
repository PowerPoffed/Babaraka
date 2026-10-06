@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist node_modules (
  echo Первый запуск: ставлю playwright...
  call npm install
)
node render.js
echo.
echo Готово. Видео в папке out
pause
