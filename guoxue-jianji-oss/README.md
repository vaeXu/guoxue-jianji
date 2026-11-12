# 国学剪辑 · Guoxue Editing

把一段古籍文本、命理断例或排盘截图，做成「老先生 + 年轻人」双人对话的**竖屏短视频**：3D 人物有口型与动作，说到哪个术语，就弹出对应的「灵动思考弹窗」。

![五行 · 洪范 弹窗效果](docs/preview/01-hongfan-wuxing.png)

本项目既是一个 [WorkBuddy](https://www.workbuddy.cn/) 技能（Skill），也是一条**可独立运行、本地离线**的短视频合成流水线。除首次安装依赖与语音合成外，不需要任何付费 API Key。

---

## 它能做什么

| 环节 | 实现 |
| --- | --- |
| 配音 | edge-tts 双音色：老先生 `zh-CN-YunjianNeural`（−8%）、命主 `zh-CN-YunxiNeural`（+2%） |
| 对口型 | Wav2Lip + 固定人脸框 `--box`，跳过逐帧人脸检测（快约 70 倍） |
| 弹窗 | PIL 逐帧渲染：弹性入场、正弦浮动、呼吸光晕、思考点、知识点逐条弹入、横向扫光 |
| 字幕 / 卡片 | 双人字幕分色、角标、整图排盘卡淡入；按字数断行且避免标点悬挂行首 |
| 成片 | ffmpeg 合成 1080×1920 / 25fps / H.264 + AAC |
| 缓存 | TTS 与对口型按文本内容哈希缓存，改台词只重算变化段 |
| 失败保护 | 对口型逐段清理陈旧结果、校验回码与产出时长、最多重试 4 次（带退避），不会静默产出截断视频 |

内容合规固定为「古籍文本解读 / 传统文化讨论」：右上角标默认为「古籍情景演绎 · 非真人测算」（可用 spec 顶层 `badge` 字段按题材改写，例如黄历类用「黄历民俗演绎 · 非运势指导」），片尾带免责声明，台词不出现算命、预测、改运、导流付费。涉及每日宜忌 / 穿衣配色这类题材时，只作文献文本解读、不对观众下建议，并注明日期时效性。详见 [`references/compliance.md`](references/compliance.md)。

### 四集示例

| 主题 | 段数 | 成片时长 | spec |
| --- | --- | --- | --- |
| 其夫发财（盲派断例） | 8 | 48.7s | [`examples/example-01-qifu-facai.json`](examples/example-01-qifu-facai.json) |
| 何为阴阳 | 5 | 50.6s | [`examples/example-02-yinyang.json`](examples/example-02-yinyang.json) |
| 何为五行 | 5 | 36.9s | [`examples/example-03-wuxing.json`](examples/example-03-wuxing.json) |
| 今日黄历宜忌与穿衣 | 5 | 48.5s | [`examples/example-04-huangli.json`](examples/example-04-huangli.json) |

更多关键帧见 [`docs/preview/`](docs/preview/)。

---

## ⚠️ 先读：许可与合规

- 本仓库采用 **CC BY-NC-SA 4.0**（署名–非商业–相同方式共享），全文见 [`LICENSE`](LICENSE)。
- 对口型依赖 [Wav2Lip](https://github.com/Rudrabha/Wav2Lip)，上游明确声明 **仅限个人 / 研究 / 非商业用途，严禁商业使用**（商用需联系 Sync Labs 授权）。因此：
  - 两个权重文件（`wav2lip_gan.pth` 416MB、`s3fd.pth` 86MB）**不随本仓库分发**，由 `scripts/setup_env.sh` 按需下载；
  - **若用于商业变现**（带货、广告、付费内容等），请先替换为可商用的唇同步方案（如 MuseTalk、LatentSync），或取得上游授权。
- `assets/characters/` 与 `assets/shots/` 是 AI 生成的形象图与动态镜头。发布到内容平台时，请按平台规则勾选「内容由 AI 生成」；再分发请遵守生成平台的服务条款。
- 中文字体使用 macOS 系统自带的 `STHeiti Medium.ttc`（Apple 专有，**不随仓库分发**）。其他平台请把脚本里的 `FONT` 常量改为本机可用的中文字体。

完整第三方声明见 [`THIRD_PARTY.md`](THIRD_PARTY.md)。

---

## 快速开始

> 实测环境：macOS / Apple Silicon / Python 3.13。Linux、Windows 需自行调整字体路径与 ffmpeg 软链方式。

```bash
git clone https://github.com/<your-account>/guoxue-jianji.git
cd guoxue-jianji

bash scripts/setup_env.sh          # 依赖 + 权重 + ffmpeg 软链 + 素材自检
mkdir -p out
python3 scripts/compose_episode.py examples/example-03-wuxing.json --out out/wuxing.mp4
```

`setup_env.sh` 会依次：

1. 检查并安装 `Pillow / numpy / edge-tts / imageio-ffmpeg`；
2. 检查并安装 `torch / librosa / scipy / tqdm`（体积较大）；
3. 下载 Wav2Lip 权重（约 500MB，国内走 hf-mirror 镜像）；
4. 建立 `vendor/bin/ffmpeg` 软链，供 Wav2Lip 内部调用；
5. 检查素材与中文字体是否齐全。

首次运行需联网（下载依赖、权重，以及 edge-tts 语音合成）；之后除 TTS 外，合成过程全部在本地完成。

### 作为 WorkBuddy 技能安装

把本仓库放到 `~/.workbuddy/skills/guoxue-jianji/` 即可，入口是 [`SKILL.md`](SKILL.md)。对 AI 说「国学剪辑：问答何为五行」并给出文案，技能会按固定流程写 spec、合成并核验成片。

---

## 写自己的一集

复制任一示例 spec，改 `segments` 即可。字段速查：

```jsonc
{
  "output": "./out/my-episode.mp4",
  "badge": "古籍情景演绎 · 非真人测算",   // 可选，覆盖右上角合规角标
  "end_card": {
    "gold_lines": ["…", "…"],
    "cream_lines": ["…", "…"],
    "cta": "…",
    "disclaimer": ["…", "…"]
  },
  "segments": [
    {
      "role": "老先生",                 // 老先生 | 命主
      "text": "台词……",               // 知识点关键词必须出现在这句里
      "shot": "MASTER",               // MASTER | VISITOR | TWO
      "box": "M",                     // M | V | T2M | T2V（与 shot 配套）
      "rate": "-8%",                  // 可选，覆盖角色默认语速
      "popup": {
        "title": "…", "sub": "…", "tag": "…",
        "y": 176,                     // 可选；双人镜头建议 980，避免遮住人物头部
        "rows": [
          {
            "no": "①", "term": "术语", "detail": "说明",
            "result": "结论", "color": "gold",
            "at": "术语",              // 台词内关键词，据此估算弹出时刻
            "at_sec": 1.2             // 或直接指定秒数（与 at 二选一）
          }
        ]
      }
    }
  ]
}
```

要点：

- `at` 写**台词中实际出现的关键词**；脚本用「关键词加权字符位置 × 语音净时长」估算弹出时刻（edge-tts 中文不返回词级时间戳，误差 < 0.3s）。
- 整图类卡片（如四柱排盘表）用 `"mode": "static"` + `"image": "cards/xxx.png"`，只做淡入。
- **双人同框（TWO）镜头请把弹窗显式设为 `"y": 980`**，否则默认位置会盖住人物头部。
- 角色与镜头默认映射：老先生 → `MASTER/M`，命主 → `VISITOR/V`，双人 → `TWO/T2M`（老先生说话）或 `TWO/T2V`（命主说话）。
- 黄历 / 宜忌 / 穿衣配色类题材：用 `badge` 与 `end_card.disclaimer` 写明「民俗解读、非运势指导」，台词只转述「黄历上写着」「网上这么说」，结尾落到「不必当定数」；`_meta` 里记清日期与数据来源，隔日发布须重出。

调试参数：

```bash
--only 5          # 只跑第 5 段（不加尾板）
--no-lipsync      # 跳过对口型，快速看画面与弹窗节奏
--no-cache        # 忽略内容缓存，强制重算
--fps 25          # 帧率
```

更多写法见 [`references/pipeline.md`](references/pipeline.md)，视觉规格见 [`references/style-guide.md`](references/style-guide.md)，已知坑见 [`references/troubleshooting.md`](references/troubleshooting.md)。

---

## 目录结构

```
SKILL.md                    WorkBuddy 技能入口（固定设定 + 6 步流程 + 硬约束）
scripts/
  compose_episode.py        主合成：配音 → 对口型 → 弹窗 → 字幕 → 拼接
  popup.py                  灵动思考弹窗逐帧渲染器
  make_cards.py             分层信息卡生成器（排盘表 / 流向卡）
  detect_face_box.py        新素材的人脸框检测（生成 --box 参数）
  setup_env.sh              环境自检与补装
references/                 pipeline / style-guide / troubleshooting / compliance
assets/
  characters/              3 张人物形象图（AI 生成，已去水印）
  shots/                   3 段 5s 动态镜头（老先生 / 命主 / 双人）
  cards/                   排盘表与流向卡透明底 PNG
  episode-spec.example.json 完整 spec 模板
examples/                  四集可直接运行的示例 spec
docs/preview/              关键帧预览图
vendor/wav2lip/            Wav2Lip 推理所需的上游代码（不含权重，见 UPSTREAM.md）
```

本仓库**不含**任何 `.pth` 权重、`*_loop.mp4` 运行时兜底长镜头、`/tmp/gxjj` 缓存与成片输出。

---

## 已知限制

- CPU 推理 Wav2Lip 较慢；Apple Silicon 上实测 MPS 反而比 CPU 慢，故脚本默认走 CPU。
- 原始镜头约 5.17s，长台词会自动把素材延展到台词长度（优先用本地 `*_loop.mp4`，缺失时由 ffmpeg 动态生成全 I 帧长镜头）。
- 连续跑多段 Wav2Lip 时本机偶发「上一段刚结束、下一段 rc=1」，脚本已加清理、退避与重试；若仍失败，可先用 `--only N` 逐段预热缓存再整集合成。
- `edge-tts` 需要联网；中文音色由微软 Edge 服务提供，服务可用性不在本项目控制范围内。
- macOS 字体路径硬编码在 `compose_episode.py` / `popup.py` / `make_cards.py` 的 `FONT` 常量，跨平台请自行修改。
- 成片定位是传统文化科普演绎，**不构成任何人生预测或建议**。

---

## 致谢

- [Wav2Lip](https://github.com/Rudrabha/Wav2Lip) — Prajwal K R 等，ACM MM 2020
- [edge-tts](https://github.com/rannyzys/edge-tts)、[imageio-ffmpeg](https://github.com/imageio/imageio-ffmpeg)、Pillow、torch、librosa
- 引文示例来自《尚书·洪范》《协纪辩方》《命理探源》《段建业盲派命理高级教程》，仅作文本解读示例

## 许可证

**CC BY-NC-SA 4.0** — 见 [`LICENSE`](LICENSE)。第三方组件各自的权利与限制见 [`THIRD_PARTY.md`](THIRD_PARTY.md)。
