@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist config.json (
  copy config.example.json config.json >nul
  echo Создан config.json. Вставьте в него адрес видеокарты и ключ RunPod, сохраните и запустите снова.
  notepad config.json
  pause
  exit /b
)
set "LIST=%~1"
if "%LIST%"=="" set /p "LIST=Перетащите сюда файл со списком (animate.txt) и нажмите Enter: "
set /p "IMG=Перетащите сюда ПАПКУ с картинками и нажмите Enter: "
node wan_cloud.js "%LIST:"=%" "%IMG:"=%"
echo.
pause
