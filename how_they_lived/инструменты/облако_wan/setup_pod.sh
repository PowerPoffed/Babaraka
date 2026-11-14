#!/bin/bash
# Скачивает в ComfyUI на арендованной видеокарте модели Wan 2.2 14B (картинка -> видео) + Lightning LoRA (4 шага), ~40 ГБ.
# Уже скачанные файлы пропускает, оборванную загрузку докачивает — можно запускать повторно.
set -e

C=""
for d in /workspace/ComfyUI /ComfyUI /workspace/*/ComfyUI /root/ComfyUI /opt/ComfyUI; do
  [ -f "$d/main.py" ] && C="$d" && break
done
[ -z "$C" ] && C=$(dirname "$(find / -maxdepth 5 -path '*ComfyUI/main.py' 2>/dev/null | head -1)")
[ -f "$C/main.py" ] || { echo "Не нашёл папку ComfyUI. Пришлите Claude скриншот этого окна."; exit 1; }
echo "ComfyUI: $C"

R=https://huggingface.co/Comfy-Org/Wan_2.2_ComfyUI_Repackaged/resolve/main/split_files
R21=https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files

dl() {
  mkdir -p "$C/models/$2"
  local out="$C/models/$2/$(basename "$1")"
  echo "== $(basename "$1")"
  curl -L -C - --retry 5 --fail -o "$out" "$1" || { echo "Ошибка загрузки. Запустите скрипт ещё раз — докачает."; exit 1; }
}

dl $R/diffusion_models/wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors diffusion_models
dl $R/diffusion_models/wan2.2_i2v_low_noise_14B_fp8_scaled.safetensors diffusion_models
dl $R/loras/wan2.2_i2v_lightx2v_4steps_lora_v1_high_noise.safetensors loras
dl $R/loras/wan2.2_i2v_lightx2v_4steps_lora_v1_low_noise.safetensors loras
dl $R/vae/wan_2.1_vae.safetensors vae
dl $R21/text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors text_encoders

echo
echo "ГОТОВО. Модели на месте. Теперь на своём компьютере запустите ОЖИВИТЬ_В_ОБЛАКЕ.bat"
