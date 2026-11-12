#!/usr/bin/env bash
# 国学剪辑 · 环境自检与补装
# 用法：bash scripts/setup_env.sh
#
# 注意：本脚本会下载 Wav2Lip 权重。Wav2Lip 上游仅限个人 / 研究 / 非商业用途，
# 严禁商业使用；商用请先替换方案或取得授权。详见 THIRD_PARTY.md。
set -u
SKILL="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY="${PYTHON:-python3}"

echo "=== 1/5 Python 依赖 ==="
MISS=""
for m in PIL numpy edge_tts imageio_ffmpeg; do
  if "$PY" -c "import $m" 2>/dev/null; then
    echo "  OK      $m"
  else
    echo "  MISSING $m"; MISS="$MISS $m"
  fi
done
if [ -n "$MISS" ]; then
  echo "  -> 安装缺失依赖（国内用清华源更快）"
  "$PY" -m pip install -q -i https://pypi.tuna.tsinghua.edu.cn/simple pillow numpy edge-tts imageio-ffmpeg || \
  "$PY" -m pip install -q pillow numpy edge-tts imageio-ffmpeg
fi

echo "=== 2/5 对口型依赖（torch / librosa）==="
if "$PY" -c "import torch, librosa" 2>/dev/null; then
  echo "  OK      torch + librosa"
else
  echo "  MISSING torch/librosa -> 安装中（体积较大，数分钟）"
  "$PY" -m pip install -q -i https://pypi.tuna.tsinghua.edu.cn/simple torch torchvision librosa scipy tqdm || \
  "$PY" -m pip install -q torch torchvision librosa scipy tqdm
fi

echo "=== 3/5 Wav2Lip 权重（不随仓库分发）==="
echo "  ⚠️  Wav2Lip 仅限个人/研究/非商业用途，商用需另行授权（见 THIRD_PARTY.md）"
W2L="$SKILL/vendor/wav2lip"
mkdir -p "$W2L/checkpoints" "$W2L/temp" "$W2L/results" "$W2L/face_detection/detection/sfd"
CKPT="$W2L/checkpoints/wav2lip_gan.pth"
S3FD="$W2L/face_detection/detection/sfd/s3fd.pth"
if [ ! -f "$CKPT" ]; then
  echo "  MISSING wav2lip_gan.pth -> 从 hf-mirror 下载（约 416MB）"
  curl -L --fail --retry 3 -o "$CKPT" "https://hf-mirror.com/camenduru/Wav2Lip/resolve/main/checkpoints/wav2lip_gan.pth" \
    || { echo "  下载失败，请手动放置该文件"; rm -f "$CKPT"; }
fi
if [ ! -f "$S3FD" ]; then
  echo "  MISSING s3fd.pth -> 从 hf-mirror 下载（约 90MB）"
  curl -L --fail --retry 3 -o "$S3FD" "https://hf-mirror.com/rippertnt/wav2lip/resolve/main/s3fd.pth" \
    || { echo "  下载失败，请手动放置该文件"; rm -f "$S3FD"; }
fi
ls -lh "$CKPT" "$S3FD" 2>&1 | sed 's/^/  /'

echo "=== 4/5 ffmpeg（imageio 自带，需在 PATH 中供 Wav2Lip 调用）==="
FF="$("$PY" -c 'import imageio_ffmpeg;print(imageio_ffmpeg.get_ffmpeg_exe())')"
mkdir -p "$SKILL/vendor/bin"
[ -e "$SKILL/vendor/bin/ffmpeg" ] || ln -sf "$FF" "$SKILL/vendor/bin/ffmpeg"
echo "  OK      $("$SKILL/vendor/bin/ffmpeg" -version 2>/dev/null | head -1)"

echo "=== 5/5 素材与字体 ==="
for f in assets/characters/char-01-master-clean.png \
         assets/shots/master.mp4 assets/shots/visitor.mp4 assets/shots/two.mp4 \
         assets/cards/card-01-bazi.png assets/episode-spec.example.json; do
  [ -f "$SKILL/$f" ] && echo "  OK      $f" || echo "  MISSING $f"
done
if [ -f "/System/Library/Fonts/STHeiti Medium.ttc" ]; then
  echo "  OK      中文字体 STHeiti Medium.ttc"
else
  echo "  MISSING macOS 字体 STHeiti Medium.ttc"
  echo "  -> 非 macOS 请把 compose_episode.py / popup.py / make_cards.py 的 FONT 常量改为本机中文字体路径"
fi

echo ""
echo "全部就绪。试跑一集："
echo "  mkdir -p out && python3 scripts/compose_episode.py examples/example-03-wuxing.json --out out/wuxing.mp4"
echo ""
echo "提示：发布到内容平台请勾选「内容由 AI 生成」；商用前请确认 Wav2Lip 授权边界。"
