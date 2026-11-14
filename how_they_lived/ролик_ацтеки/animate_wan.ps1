# Анимация ключевых кадров через Wan 2.2 5B (How They Lived)
# ComfyUI должен быть запущен (127.0.0.1:8188), модели Wan 2.2 скачаны.
# Запуск: правой кнопкой -> "Выполнить с помощью PowerShell" или командой из инструкции.
$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.Net.Http
Add-Type -AssemblyName System.Windows.Forms
$Comfy  = "http://127.0.0.1:8188"
$Frames = 73          # 73 кадра = 3 секунды при 24 fps
$Steps  = 6           # быстрый режим с FastWan LoRA (проверено: ~2,5 мин на клип)
$NEG = "色调艳丽，过曝，静态，细节模糊不清，字幕，静止，整体发灰，最差质量，低质量，JPEG压缩残留，丑陋的，残缺的，多余的手指，画得不好的手部，画得不好的脸部，畸形的，毁容的，形态畸形的肢体，手指融合，静止不动的画面，杂乱的背景，三条腿，背景人很多，倒着走, morphing, distorted face, text, watermark"

try { Invoke-RestMethod "$Comfy/system_stats" | Out-Null } catch { Write-Host "ComfyUI не отвечает на $Comfy. Запустите ComfyUI и попробуйте снова." -ForegroundColor Red; Read-Host "Enter"; exit }

$ofd = New-Object System.Windows.Forms.OpenFileDialog
$ofd.Title = "Выберите список: animate_first_minute.txt (или animate.txt)"; $ofd.Filter = "Текст (*.txt)|*.txt"
if ($ofd.ShowDialog() -ne "OK") { exit }
$fbd = New-Object System.Windows.Forms.FolderBrowserDialog
$fbd.Description = "Выберите папку с ВЫБРАННЫМИ картинками (final)"
if ($fbd.ShowDialog() -ne "OK") { exit }
$imgDir = $fbd.SelectedPath
$outDir = Join-Path (Split-Path $imgDir) "video_clips"
New-Item -ItemType Directory -Force $outDir | Out-Null
Write-Host "Клипы будут сохраняться в: $outDir" -ForegroundColor Cyan

$client = New-Object System.Net.Http.HttpClient
$client.Timeout = [TimeSpan]::FromMinutes(10)
function Upload-Image($path) {
    $content = New-Object System.Net.Http.MultipartFormDataContent
    $bytes = [System.IO.File]::ReadAllBytes($path)
    $fc = New-Object -TypeName System.Net.Http.ByteArrayContent -ArgumentList (,$bytes)
    $fc.Headers.ContentType = [System.Net.Http.Headers.MediaTypeHeaderValue]::Parse("image/png")
    $content.Add($fc, "image", [System.IO.Path]::GetFileName($path))
    $content.Add((New-Object System.Net.Http.StringContent("true")), "overwrite")
    $r = $client.PostAsync("$Comfy/upload/image", $content).Result
    return ($r.Content.ReadAsStringAsync().Result | ConvertFrom-Json).name
}
function New-Workflow($img, $prompt, $seed, $prefix) {
    return @{
      "1"=@{class_type="UNETLoader";inputs=@{unet_name="wan2.2_ti2v_5B_fp16.safetensors";weight_dtype="default"}}
      "2"=@{class_type="CLIPLoader";inputs=@{clip_name="umt5_xxl_fp8_e4m3fn_scaled.safetensors";type="wan";device="default"}}
      "3"=@{class_type="VAELoader";inputs=@{vae_name="wan2.2_vae.safetensors"}}
      "13"=@{class_type="LoraLoaderModelOnly";inputs=@{model=@("1",0);lora_name="Wan2_2_5B_FastWanFullAttn_lora_rank_128_bf16.safetensors";strength_model=0.7}}
      "4"=@{class_type="ModelSamplingSD3";inputs=@{model=@("13",0);shift=8.0}}
      "5"=@{class_type="CLIPTextEncode";inputs=@{clip=@("2",0);text=$prompt}}
      "6"=@{class_type="CLIPTextEncode";inputs=@{clip=@("2",0);text=$NEG}}
      "7"=@{class_type="LoadImage";inputs=@{image=$img}}
      "8"=@{class_type="Wan22ImageToVideoLatent";inputs=@{vae=@("3",0);width=1280;height=704;length=$Frames;batch_size=1;start_image=@("7",0)}}
      "9"=@{class_type="KSampler";inputs=@{model=@("4",0);seed=$seed;steps=$Steps;cfg=1.0;sampler_name="euler";scheduler="simple";denoise=1.0;positive=@("5",0);negative=@("6",0);latent_image=@("8",0)}}
      "10"=@{class_type="VAEDecode";inputs=@{samples=@("9",0);vae=@("3",0)}}
      "11"=@{class_type="CreateVideo";inputs=@{images=@("10",0);fps=24.0}}
      "12"=@{class_type="SaveVideo";inputs=@{video=@("11",0);filename_prefix=$prefix;format="auto";codec="auto"}}
    }
}

$lines = Get-Content -Path $ofd.FileName -Encoding UTF8 | Where-Object { $_ -match "\|" }
$i = 0
foreach ($line in $lines) {
    $i++
    $shot, $motion = $line.Split("|", 2)
    $outFile = Join-Path $outDir "$shot.mp4"
    if (Test-Path $outFile) { Write-Host "[$i/$($lines.Count)] $shot уже есть, пропускаю"; continue }
    $img = Get-ChildItem $imgDir -File | Where-Object { $_.BaseName -like "$shot*" -and $_.Extension -match "png|jpg|jpeg|webp" } | Select-Object -First 1
    if (-not $img) { Write-Host "[$i/$($lines.Count)] $shot — картинка не найдена в $imgDir, пропускаю" -ForegroundColor Yellow; continue }
    Write-Host "[$i/$($lines.Count)] $shot ... " -NoNewline
    $t0 = Get-Date
    $up = Upload-Image $img.FullName
    $wf = New-Workflow $up $motion (Get-Random -Minimum 1 -Maximum 2000000000) "how_they_lived_clips/$shot"
    $json = @{ prompt = $wf } | ConvertTo-Json -Depth 12 -Compress
    $resp = Invoke-RestMethod -Uri "$Comfy/prompt" -Method Post -ContentType "application/json; charset=utf-8" -Body ([System.Text.Encoding]::UTF8.GetBytes($json))
    $promptId = $resp.prompt_id
    $done = $false
    while (-not $done) {
        Start-Sleep -Seconds 5
        $h = Invoke-RestMethod "$Comfy/history/$promptId"
        $item = $h.$promptId
        if ($item) {
            if ($item.status.status_str -eq "error") {
                Write-Host "ОШИБКА" -ForegroundColor Red
                $item.status.messages | ConvertTo-Json -Depth 6 | Write-Host
                Write-Host "Пришлите Claude скриншот этого окна." -ForegroundColor Red; Read-Host "Enter"; exit
            }
            foreach ($node in $item.outputs.PSObject.Properties) {
                foreach ($key in @("images","videos","gifs")) {
                    foreach ($f in $node.Value.$key) {
                        if ($f.filename -match "\.(mp4|webm|mkv)$") {
                            $q = "filename=" + [uri]::EscapeDataString($f.filename) + "&subfolder=" + [uri]::EscapeDataString($f.subfolder) + "&type=output"
                            Invoke-WebRequest -Uri "$Comfy/view?$q" -OutFile $outFile -UseBasicParsing
                            $done = $true
                        }
                    }
                }
            }
        }
    }
    $sec = [int]((Get-Date) - $t0).TotalSeconds
    Write-Host "готово за $sec сек" -ForegroundColor Green
}
Write-Host "`nВСЁ ГОТОВО. Клипы в папке: $outDir" -ForegroundColor Green
Read-Host "Нажмите Enter, чтобы закрыть"
