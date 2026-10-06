@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist node_modules (
  echo Первый запуск: ставлю playwright...
  call npm install
)
set "PLAN=%~1"
if "%PLAN%"=="" set "PLAN=..\ролик_сон\motion_plan.json"
node render.js "%PLAN%"
echo.
echo Готово. Видео в папке out
pause
