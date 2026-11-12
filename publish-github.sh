#!/usr/bin/env bash
# 把 guoxue-jianji-oss 发布到 GitHub（需先完成 `gh auth login`）
#
# 用法：
#   gh auth login --web --git-protocol https     # 一次性网页授权
#   bash publish-github.sh [repo-name] [public|private]
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$ROOT/guoxue-jianji-oss"
REPO="${1:-guoxue-jianji}"
VIS="${2:-public}"

command -v gh >/dev/null || { echo "缺少 gh CLI：brew install gh"; exit 1; }
gh auth status >/dev/null 2>&1 || { echo "尚未登录 GitHub：先执行 gh auth login --web"; exit 1; }

cd "$REPO_DIR"

# 用 GitHub 账户真实身份提交（避免占位作者信息进入公开历史）
GH_LOGIN="$(gh api user --jq .login)"
GH_NAME="$(gh api user --jq '.name // .login')"
GH_EMAIL="$(gh api user --jq '.email // empty')"
if [ -z "$GH_EMAIL" ]; then
  GH_ID="$(gh api user --jq .id)"
  GH_EMAIL="${GH_ID}+${GH_LOGIN}@users.noreply.github.com"
fi
git config user.name "$GH_NAME"
git config user.email "$GH_EMAIL"

if ! git rev-parse --verify HEAD >/dev/null 2>&1; then
  git add -A
  git commit -m "Initial release: 国学剪辑 / Guoxue Editing

古籍情景演绎竖屏短视频合成流水线：edge-tts 双音色配音、
Wav2Lip 固定框对口型、PIL 灵动思考弹窗、字幕与片尾免责。

含三集示例 spec 与关键帧预览。权重不入库，由 setup_env.sh 按需下载。
许可 CC BY-NC-SA 4.0；第三方组件见 THIRD_PARTY.md。"
fi

echo "==> 创建 $VIS 仓库 $GH_LOGIN/$REPO 并推送 ..."
gh repo create "$REPO" --"$VIS" --source=. --remote=origin --push \
  --description "国学剪辑 · 古籍情景演绎竖屏短视频合成流水线（WorkBuddy Skill）"
echo "==> 完成：$(gh repo view "$GH_LOGIN/$REPO" --json url --jq .url)"
