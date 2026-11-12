# vendor/wav2lip — 上游代码说明

本目录是 [Rudrabha/Wav2Lip](https://github.com/Rudrabha/Wav2Lip)（ACM MM 2020）推理所需代码的副本，随本项目提供以便开箱运行。

## 许可（重要）

上游 README 明确声明：**仅限个人 / 研究 / 非商业用途，严禁商业使用**；商用需联系 Sync Labs（`rudrabha@synclabs.so` / `prajwal@synclabs.so`）。GitHub 标记为 `NOASSERTION`。

完整声明见仓库根目录 [`THIRD_PARTY.md`](../../THIRD_PARTY.md)。

## 内容与改动

- **不含任何 `.pth` 权重**（`checkpoints/wav2lip_gan.pth`、`face_detection/detection/sfd/s3fd.pth`），由 `scripts/setup_env.sh` 按需下载。
- 移除了原始上游 README（其内容为 Sync Labs 托管 API 的 quickstart，与本项目的本地推理无关，易造成误导）。
- 为在 Python 3.13 / torch 2.x / librosa 新版下运行，做了如下兼容性修改：
  - `inference.py`：`torch.load(..., weights_only=False)`；支持通过 `--box` 固定人脸框以跳过 s3fd 逐帧检测；输出写入 `temp/result.avi`。
  - `audio.py`：`librosa.filters.mel(...)` 改为关键字参数，适配新版 librosa。
  - `hparams.py` / `models/`：保持上游结构，未改动模型定义。
- 其余训练、评估相关脚本为上游随附文件，本项目推理流程不会调用，保留以便溯源。

## 本项目如何使用它

`scripts/compose_episode.py` 以 `cwd=vendor/wav2lip` 调用 `inference.py`，传入固定 `--box` 与延展到台词长度的镜头视频，读回 `temp/result.avi` 再与配音合成。固定框坐标见 `scripts/detect_face_box.py` 与主脚本 `BOX` 常量。
