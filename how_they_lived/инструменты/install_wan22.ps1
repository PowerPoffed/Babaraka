# Установка Wan 2.2 5B (картинка -> видео) для ComfyUI
# Скрипт сам находит папки по уже установленным моделям Z-Image и кладёт файлы рядом.
$ErrorActionPreference = "Stop"

function Find-ModelDir($fileName) {
    Write-Host "Ищу $fileName ..."
    $roots = @("$env:USERPROFILE", "C:\", "D:\", "E:\") | Where-Object { Test-Path $_ }
    foreach ($r in $roots) {
        $f = Get-ChildItem -Path $r -Recurse -Depth 9 -Filter $fileName -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($f) { Write-Host "  найдено: $($f.DirectoryName)"; return $f.DirectoryName }
    }
    throw "Не нашёл $fileName. Пришлите Claude скриншот папки ComfyUI\models."
}

$diffDir = Find-ModelDir "z_image_turbo_int8_convrot.safetensors"
$textDir = Find-ModelDir "qwen_3_4b_fp8_mixed.safetensors"
$vaeDir  = Find-ModelDir "ae.safetensors"

$drive = (Get-Item $diffDir).PSDrive
$freeGB = [math]::Round($drive.Free / 1GB, 1)
Write-Host "Свободно на диске $($drive.Name): $freeGB ГБ (нужно ~18 ГБ)"
if ($freeGB -lt 19) { throw "Мало места на диске. Освободите место и запустите снова." }

$files = @(
  @{url="https://huggingface.co/Comfy-Org/Wan_2.2_ComfyUI_Repackaged/resolve/main/split_files/diffusion_models/wan2.2_ti2v_5B_fp16.safetensors"; dir=$diffDir},
  @{url="https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors"; dir=$textDir},
  @{url="https://huggingface.co/Comfy-Org/Wan_2.2_ComfyUI_Repackaged/resolve/main/split_files/vae/wan2.2_vae.safetensors"; dir=$vaeDir}
)
foreach ($f in $files) {
    $name = Split-Path $f.url -Leaf
    $out = Join-Path $f.dir $name
    Write-Host "`nСкачиваю $name -> $($f.dir)"
    # -C - докачивает, если загрузка прервалась: просто запустите скрипт ещё раз
    & curl.exe -L -C - --retry 5 -o $out $f.url
    if ($LASTEXITCODE -ne 0) { throw "Ошибка загрузки $name. Запустите скрипт ещё раз — докачает." }
}
Write-Host "`nГОТОВО. Перезапустите ComfyUI, чтобы он увидел новые модели." -ForegroundColor Green
