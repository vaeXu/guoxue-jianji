# 第三方组件与权利声明

本仓库**自研部分**——`scripts/compose_episode.py`、`scripts/popup.py`、`scripts/make_cards.py`、`scripts/detect_face_box.py`、`scripts/setup_env.sh`、`SKILL.md`、`references/`、`examples/`、`docs/preview/` 中由本项目创作的图文——采用 **CC BY-NC-SA 4.0**，全文见 [`LICENSE`](LICENSE)。

以下第三方组件**不适用**上述许可，各自权利归原作者所有。

---

## 1. Wav2Lip（对口型）— ⚠️ 仅限非商业

- 上游：https://github.com/Rudrabha/Wav2Lip
- 论文：Prajwal K R, Mukhopadhyay R, Namboodiri V P, Jawahar C V. *A Lip Sync Expert Is All You Need for Speech to Lip Generation In the Wild*, ACM Multimedia 2020.
- **许可**：上游 README 明确声明 *"This repository can only be used for personal/research/non-commercial purposes"*，**严禁任何形式的商业使用**；商业授权需联系 `rudrabha@synclabs.so` / `prajwal@synclabs.so`（Sync Labs）。GitHub 将其标为 `NOASSERTION`。
- 本仓库在 `vendor/wav2lip/` 保留了推理所需的上游代码副本，并做了兼容性修改（详见该目录 `UPSTREAM.md`）。这些代码同样受上游的非商业限制约束。
- **本仓库不分发任何模型权重**。运行时由 `scripts/setup_env.sh` 从第三方镜像下载：
  | 文件 | 体积 | 来源 |
  | --- | --- | --- |
  | `checkpoints/wav2lip_gan.pth` | 416MB | `hf-mirror.com/camenduru/Wav2Lip` |
  | `face_detection/detection/sfd/s3fd.pth` | 86MB | `hf-mirror.com/rippertnt/wav2lip` |

  这两个权重由上游 / 第三方镜像发布者提供，其下载与使用须遵守各自条款；镜像地址仅为国内网络可达性考虑，不代表本项目对其权利作任何担保。
- **若需商用**：请移除 Wav2Lip 依赖，改用明确允许商用的唇同步方案（例如 MuseTalk、LatentSync 等），或自行取得上游授权。

## 2. face_alignment / S3FD（人脸检测）

`vendor/wav2lip/face_detection/` 源自 [1adrianb/face-alignment](https://github.com/1adrianb/face-alignment)，由 Wav2Lip 上游随附。本项目使用固定 `--box` 跳过逐帧检测，因此运行时**不需要** `s3fd.pth` 也能完成对口型；该权重仍被 `setup_env.sh` 一并下载以兼容上游代码路径。权利归原作者。

## 3. Python 依赖（仅调用，不随仓库再分发）

`edge-tts`、`imageio-ffmpeg`、`Pillow`、`numpy`、`torch`、`torchvision`、`librosa`、`scipy`、`tqdm`、`opencv-python`。各自许可以其官方仓库为准，本项目不含其源码。

其中 `imageio-ffmpeg` 随包提供 ffmpeg 二进制，`scripts/setup_env.sh` 会在 `vendor/bin/` 建立软链供 Wav2Lip 内部调用；该软链已列入 `.gitignore`，不入库。

## 4. 字体

`STHeiti Medium.ttc` 是 macOS 系统字体，Apple 专有，**不随本仓库分发**，脚本仅在运行时读取。非 macOS 环境请把 `compose_episode.py` / `popup.py` / `make_cards.py` 中的 `FONT` 常量改为本机可用的中文字体；由此产生的字形差异与本项目无关。

## 5. AI 生成素材

`assets/characters/*.png`（3 张人物形象）与 `assets/shots/*.mp4`（3 段动态镜头）由 WorkBuddy 的 ImageGen / VideoGen 生成，仅用于演示本流水线。再分发与商用请遵守生成平台的服务条款；发布到内容平台时应按平台要求标注「内容由 AI 生成」。

## 6. 古籍引文

`examples/` 与 `docs/preview/` 中出现的引文来自《尚书·洪范》《协纪辩方》《命理探源》《段建业盲派命理高级教程》等，仅作为传统文化文本解读的示例，不代表对任何具体人的推断或建议。

---

**免责**：本文件为便利说明，不构成法律意见。若对再分发范围、商用边界有疑问，请以各上游仓库的正式许可文本为准，或咨询专业人士。
