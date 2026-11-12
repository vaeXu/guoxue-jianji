---
name: guoxue-jianji
display_name_zh: 国学剪辑
display_name_en: Guoxue Editing
description: 国学剪辑（Guoxue Editing）——把一段古籍文本、命理断例或一张排盘截图，做成「老先生 + 命主」双人对话的情景演绎竖屏短视频：3D 人物有口型与动作，说到哪个术语就弹出对应的灵动思考弹窗。当用户给出文字或图片并要求做成这类国学短视频，或提到「国学剪辑」「按上次那套流程」「古籍情景演绎」「排盘弹窗视频」时使用本技能。
agent_created: true
---

# 国学剪辑 · 固定流程

把「一段文字或一张图片」做成一条 **1080×1920 竖屏短视频**：民国书斋里，一位老先生与一位命主对话，人物会动、会说话，说到哪个术语就弹出对应的思考弹窗。

**场景、形象、音色一律沿用本技能自带的素材，不要替换、不要重新生成**（除非用户明确要求换风格）。

> 本文件是 WorkBuddy 技能入口；仓库版的安装、许可与第三方声明见 `README.md` / `THIRD_PARTY.md`。

## 固定设定（不可改）

| 项 | 值 | 位置 |
| --- | --- | --- |
| 场景 | 民国书斋暖光，一桌两凳，油灯 | `assets/shots/*.mp4` |
| 老先生 | 银白须发、圆框眼镜、深青灰长衫 | `assets/characters/char-01-master-clean.png` |
| 命主 | 短发、月白长衫 | `assets/characters/char-02-visitor-clean.png` |
| 双人同框 | 老先生左 / 命主右 | `assets/characters/scene-03-two-shot-clean.png` |
| 老先生音色 | edge-tts `zh-CN-YunjianNeural`，语速 −8% | 脚本内置 |
| 命主音色 | edge-tts `zh-CN-YunxiNeural`，语速 +2% | 脚本内置 |
| 版式 | 1080×1920 / 25fps；右上角标「古籍情景演绎 · 非真人测算」；底部字幕条；片尾免责 | `scripts/compose_episode.py` |
| 弹窗 | 灵动思考弹窗（弹性入场 + 浮动 + 呼吸光晕 + 思考点 + 逐条弹入 + 扫光） | `scripts/popup.py` |

## 执行流程

### 0. 环境自检（首次运行或报缺依赖时）
```bash
bash scripts/setup_env.sh
```
torch / librosa / edge-tts / imageio-ffmpeg / Wav2Lip 权重 / ffmpeg 软链 / 素材 / 字体，逐项自检并补装。

> ⚠️ Wav2Lip 上游**仅限个人 / 研究 / 非商业用途**，商用需替换方案或取得授权。见 `THIRD_PARTY.md`。

### 1. 读料（不许推测）
- **给图片**：用读图工具逐字提取可见内容（干支、书名、日期、正文、按钮文字），只写图上实际可见的。
- **给文字**：直接作为素材文本。
- **多图或多源信息冲突**：明确列出冲突点并提醒用户核对（如两图时柱分别为「丙辰」与「己未」），不要自行选一个。

### 2. 写文案（口播稿）
- 定位为「古籍文本解读 / 传统文化讨论」，**不出现**算命、预测、改运、加微信、付费咨询。
- 不对真人做推断；历史案例天然是安全边界。
- 篇幅：约 300–420 字 / 12 段左右；若要求控制在 1 分钟内，按 5–8 段、约 150–200 字安排。

### 3. 写双人对话剧本
- 结构：命主递上材料 → 老先生「不急着断吉凶」引出书上的词 → 逐个知识点（每个知识点恰好在某一小段被说出）→ 命主追问 → 老先生收束。
- 每个知识点必须落在**一句台词**里，这样弹窗能对上时间点。
- 详见 `references/pipeline.md`。

### 4. 写 spec JSON
复制 `assets/episode-spec.example.json` 或 `examples/` 里的示例改写。字段速查：

```jsonc
{
  "output": "./out/episode.mp4",
  "end_card": { "gold_lines": [], "cream_lines": [], "cta": "", "disclaimer": [] },
  "segments": [{
    "role": "老先生",              // 老先生 | 命主
    "text": "台词……",              // 知识点关键词必须出现在台词里
    "shot": "MASTER",              // MASTER | VISITOR | TWO
    "box": "M",                    // M | V | T2M | T2V（与 shot 配套）
    "popup": {
      "title": "多途径做功",
      "sub": "副标题",
      "tag": "古籍断例 ②",
      "y": 176,                    // 可选；双人镜头务必设 980，见下
      "rows": [{
        "no": "①", "term": "合用", "detail": "癸水合年干戊土正官",
        "result": "名 / 位置", "color": "gold", "at": "合用"   // at=台词内关键词
      }]
    }
  }]
}
```
- `at` 写**台词中实际出现的关键词**，脚本据此估算弹出时刻；也可直接给 `"at_sec": 1.2` 指定秒数。
- 整图类卡片（如四柱排盘表）用 `"mode": "static"` + `"image": "cards/xxx.png"`，只做淡入，不套气泡动效。
- 角色与镜头默认映射：老先生→MASTER/M，命主→VISITOR/V，开场与收尾双人→TWO/T2V 或 TWO/T2M。
- **双人同框（TWO）镜头的弹窗必须显式设 `"y": 980`**：该镜头人物头部位置偏上，默认弹窗会把两张脸盖住；980 会把弹窗移到桌面前方的下半部空白区，且不与字幕重叠。

### 5. 合成
```bash
python3 scripts/compose_episode.py <spec.json> --out ./out/out.mp4
```
- 单段调试：`--only 5`（只跑第 5 段，不加尾板）。
- 跳过对口型快速看画面：`--no-lipsync`。
- 配音与对口型按内容哈希缓存在 `/tmp/gxjj/cache`，改台词重跑会自动重算，未改段落不重复消耗时间。
- 全片 12 段约 3–5 分钟，其中对口型占大头。

### 6. 核验与交付
- 抽帧确认：弹窗不遮脸、字幕完整、卡片逐条出现时机正确、人物在动。
- 音量检查：`ffmpeg -i out.mp4 -af volumedetect -f null -`。
- 交付成片 mp4 + 关键帧 png，并附上发布提醒（见 `references/compliance.md`）。

## 硬性约束

1. **不擅自安装技能/改素材/换形象音色**；需要动用 ImageGen / VideoGen 生成新形象时，先说明积分成本并取得用户同意（正常流程复用既有素材，零积分）。
2. **不删用户文件**；脚本里也不要对目录做 `shutil.rmtree`（会被安全策略拦截），临时目录用 UUID 命名即可。
3. 抖音发布提醒固定包含：后台勾选「内容由 AI 生成」声明；古籍来源与数据核对提示。
4. 对口型结果必须与配音时长齐平；脚本已内置「清理陈旧 result.avi + 失败重试 3 次 + 时长校验」，不要绕过这些校验。

## 文件索引

- `scripts/compose_episode.py` — 主合成脚本（配音 → 对口型 → 弹窗 → 字幕 → 成片）
- `scripts/popup.py` — 灵动思考弹窗渲染器（可单独预览）
- `scripts/make_cards.py` — 分层信息卡生成器（排盘表 / 流向卡模板）
- `scripts/detect_face_box.py` — 新素材的人脸框检测（生成 Wav2Lip `--box` 参数）
- `scripts/setup_env.sh` — 环境自检与补装
- `references/pipeline.md` — 文案/剧本/spec 写法详解
- `references/style-guide.md` — 固定设定与视觉规格
- `references/troubleshooting.md` — 已知坑与解法
- `references/compliance.md` — 抖音发布合规要点
- `examples/` — 三集可直接运行的示例 spec
- `README.md` / `THIRD_PARTY.md` / `LICENSE` — 开源说明、第三方声明与许可证
