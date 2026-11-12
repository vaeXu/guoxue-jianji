# 国学剪辑 · Guoxue Editing

**把一段古籍文本、命理断例或排盘截图，变成「老先生 + 年轻人」对话的竖屏短视频。**
3D 人物有口型与动作，说到哪个术语，就弹出对应的「灵动思考弹窗」——一页古籍，一分钟讲完。

![Python 3.13](https://img.shields.io/badge/Python-3.13-blue) ![1080×1920](https://img.shields.io/badge/输出-1080×1920_竖屏-orange) ![本地离线](https://img.shields.io/badge/合成-本地离线-green) ![CC BY-NC-SA 4.0](https://img.shields.io/badge/License-CC%20BY--NC--SA%204.0-lightgrey)

<p>
  <img src="docs/preview/01-hongfan-wuxing.png" width="196" alt="五行·洪范 弹窗">
  <img src="docs/preview/02-yinyang-taiji.png" width="196" alt="阴阳·太极 弹窗">
  <img src="docs/preview/03-qifu-facai.png" width="196" alt="其夫发财 断例弹窗">
  <img src="docs/preview/04-huangli-minSu.png" width="196" alt="黄历民俗 双人同框">
</p>

> 上面四张都是**成片真实截帧**。完整示例见 [`docs/preview/`](docs/preview/)。

它既是一个 [WorkBuddy](https://www.workbuddy.cn/) 技能，也是一条可独立运行的本地合成流水线。除首次安装依赖与语音合成外，**不需要任何付费 API Key**。

---

## 30 秒上手

> 实测环境：macOS / Apple Silicon / Python 3.13。Linux、Windows 需自行调整字体路径与 ffmpeg 软链方式。

```bash
git clone <仓库地址> && cd guoxue-jianji
bash scripts/setup_env.sh          # 依赖 + 权重 + ffmpeg 软链 + 素材自检
mkdir -p out
python3 scripts/compose_episode.py examples/example-03-wuxing.json --out out/wuxing.mp4
```

`setup_env.sh` 会装好 Python 依赖、下载 Wav2Lip 权重（约 500MB）、建立 ffmpeg 软链并检查素材与中文字体。首次运行需联网（下载依赖、权重，以及 edge-tts 语音合成）；**之后除配音外，合成全程在本地完成**。

想直接在对话里用？把本仓库放到 `~/.workbuddy/skills/guoxue-jianji/`，然后说「国学剪辑：问答何为五行」。入口见 [`SKILL.md`](SKILL.md)。

---

## 四集示例

| 主题 | 段数 | 时长 | 直接运行 |
| --- | --- | --- | --- |
| 其夫发财（盲派断例） | 8 | 48.7s | [`example-01-qifu-facai.json`](examples/example-01-qifu-facai.json) |
| 何为阴阳 | 5 | 50.6s | [`example-02-yinyang.json`](examples/example-02-yinyang.json) |
| 何为五行 | 5 | 36.9s | [`example-03-wuxing.json`](examples/example-03-wuxing.json) |
| 今日黄历宜忌与穿衣 | 5 | 48.5s | [`example-04-huangli.json`](examples/example-04-huangli.json) |

四集成片均为 **1080×1920 / 25fps / H.264 + AAC**，控制在 1 分钟内。改 spec 里的 `segments` 就能出自己的一集。

---

## 一分钟看懂流程

```
spec.json（台词 + 知识点）
   → edge-tts 双音色配音（老先生 云健 −8% / 命主 云希 +2%）
   → Wav2Lip 对口型（固定人脸框，跳过逐帧检测）
   → PIL 逐帧渲染灵动弹窗 + 分色字幕 + 片尾免责卡
   → ffmpeg 拼接成片
```

弹窗支持弹性入场、逐条弹入、思考点与横向扫光；知识点按台词节奏错峰出现。TTS 与对口型按文本内容哈希缓存，**改台词只重算变化的段**。对口型逐段校验时长并带重试，不会静默产出截断视频。

---

## 写自己的一集

复制任一示例，改 `segments`。最小可用结构：

```jsonc
{
  "output": "./out/my-episode.mp4",
  "badge": "古籍情景演绎 · 非真人测算",   // 可选：覆盖右上角合规角标
  "end_card": {
    "gold_lines": ["……", "……"],
    "cream_lines": ["……", "……"],
    "cta": "……",
    "disclaimer": ["本视频为古籍文本情景演绎，仅作传统文化讨论", "不构成任何人生预测或建议"]
  },
  "segments": [
    {
      "role": "老先生",                 // 老先生 | 命主
      "text": "《尚书·洪范》有云：一曰水，二曰火……",
      "shot": "MASTER",                // MASTER | VISITOR | TWO
      "box": "M",                      // M | V | T2M | T2V
      "popup": {
        "title": "五行 · 洪范", "sub": "《尚书·洪范》｜五行之目", "tag": "古籍溯源",
        "y": 176,                      // 双人镜头务必设 980，否则弹窗会盖住人脸
        "rows": [
          { "no": "①", "term": "水火木金土", "detail": "五行之目",
            "result": "洪范所立", "color": "gold", "at_sec": 1.2 }
        ]
      }
    }
  ]
}
```

**四条要点**

- `at` 写台词里**实际出现的关键词**，脚本据此估算弹出时刻；也可直接用 `at_sec` 指定秒数。
- 双人同框（`TWO`）镜头必须显式设 `"y": 980`。整图类卡片用 `"mode": "static"` + `"image": "cards/xxx.png"`。
- 角色默认映射：老先生 → `MASTER/M`，命主 → `VISITOR/V`，双人 → `TWO/T2M`（老先生说话）。
- 黄历 / 宜忌 / 穿衣类题材：用 `badge` 与 `disclaimer` 写明「民俗解读、非运势指导」，台词只转述「黄历上写着……」，结尾落到「不必当定数」；在 `_meta` 记清日期与来源，**隔日发布须重出**。详见 [`references/compliance.md`](references/compliance.md)。

调试：`--only 5` 只跑第 5 段、`--no-lipsync` 跳过对口型看画面节奏、`--no-cache` 强制重算、`--fps 25` 改帧率。

完整字段与视觉规格见 [`references/pipeline.md`](references/pipeline.md)、[`references/style-guide.md`](references/style-guide.md)、[`assets/episode-spec.example.json`](assets/episode-spec.example.json)。

---

## ⚠️ 许可与合规（发布前必读）

| 事项 | 说明 |
| --- | --- |
| **本仓库许可** | [CC BY-NC-SA 4.0](LICENSE)：署名–非商业–相同方式共享 |
| **对口型组件** | [Wav2Lip](https://github.com/Rudrabha/Wav2Lip) 上游声明**仅限个人 / 研究 / 非商业，严禁商用**（商用需联系 Sync Labs 授权） |
| **权重不分发** | `wav2lip_gan.pth` 416MB、`s3fd.pth` 86MB 不在仓库内，由 `setup_env.sh` 按需下载 |
| **商业变现** | 带货、广告、付费内容等场景，请先换成可商用唇同步方案（MuseTalk / LatentSync）或取得上游授权 |
| **AI 素材** | `assets/` 的人物形象与镜头为 AI 生成；发布到内容平台需按平台规则勾选「内容由 AI 生成」 |
| **内容口径** | 成片定位为古籍文本情景演绎，台词不出现算命、预测、改运、导流付费，**不构成任何人生预测或建议** |
| **中文字体** | 依赖 macOS 自带 `STHeiti Medium.ttc`（Apple 专有，不随仓库分发）；其他平台请改脚本 `FONT` 常量 |

完整第三方权利声明见 [`THIRD_PARTY.md`](THIRD_PARTY.md)，平台发布细则见 [`references/compliance.md`](references/compliance.md)。

---

## 已知限制

- CPU 推理 Wav2Lip 较慢；Apple Silicon 上实测 MPS 反而比 CPU 慢，脚本默认走 CPU。
- 原始镜头约 5.17s，长台词会自动延展素材（优先用本地 `*_loop.mp4`，缺失时动态生成全 I 帧长镜头）。
- 连续跑多段时本机偶发「上一段刚结束、下一段 rc=1」；脚本已加清理、退避与重试，若仍失败可用 `--only N` 逐段预热缓存。见 [`references/troubleshooting.md`](references/troubleshooting.md)。
- `edge-tts` 需联网，中文音色由微软 Edge 服务提供，服务可用性不在本项目控制范围内。

---

## 致谢与许可证

引文示例取自《尚书·洪范》《协纪辩方》《命理探源》《段建业盲派命理高级教程》，仅作文本解读示例。依赖致谢：[Wav2Lip](https://github.com/Rudrabha/Wav2Lip)（Prajwal K R 等，ACM MM 2020）、[edge-tts](https://github.com/rannyzys/edge-tts)、[imageio-ffmpeg](https://github.com/imageio/imageio-ffmpeg)、Pillow、torch、librosa。

**CC BY-NC-SA 4.0** — 全文见 [`LICENSE`](LICENSE)；第三方组件各自的权利与限制见 [`THIRD_PARTY.md`](THIRD_PARTY.md)。
