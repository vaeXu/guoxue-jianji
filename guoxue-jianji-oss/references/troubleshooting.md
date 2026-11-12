# 已知坑与解法

## Python / 依赖

| 现象 | 原因 | 解法 |
| --- | --- | --- |
| `pip install torch` 卡住 20 分钟 | PyPI 直连慢 | 换清华源 `-i https://pypi.tuna.tsinghua.edu.cn/simple` |
| `torch.load` 报 `weights_only` 拒绝加载 | torch 2.6+ 默认 `weights_only=True` | 加载处加 `weights_only=False`（已在 `vendor/wav2lip` 内打好补丁） |
| `librosa.filters.mel()` 报位置参数错误 | librosa 1.0 改签名 | 改用关键字 `librosa.filters.mel(sr=..., n_fft=..., n_mels=...)`（已修） |
| `import librosa` 报 numpy 兼容错 | numpy 2.x | 升级 librosa，或 `pip install "numpy<2"` |

## Wav2Lip

| 现象 | 原因 | 解法 |
| --- | --- | --- |
| **成片比台词总时长短一大截**（长台词段落被截到 ~6.3s） | Wav2Lip 输出帧数 = `min(素材帧数, 音频 mel 段数)`，素材只有 5.17s，超过就断；合成时 `-shortest` 把截断带到成片 | 对口型前先**延展素材**：乒乓（正+反 concat）再按台词长度循环，见 `compose_episode.py::prepare_loop_video`；脚本会按 wav 时长校验缓存，短的自动重算 |
| 合成时被单帧 PNG 截断 | `-shortest` 遇到时长 1 帧的图片输入 | 字幕层等图片输入统一加 `-loop 1` |
| `inference.py` 最后一步 `ffmpeg: command not found` | 本机 ffmpeg 由 imageio 自带，不在 PATH | 脚本把 `vendor/bin` 加进 PATH；`vendor/bin/ffmpeg` 是 imageio 二进制软链 |
| `result.avi` 缺失 | 上一步推理失败 | 读 `inference.py` 的 stderr；确认权重与 s3fd 都在位 |
| 跑 6 秒要 5–6 分钟 | 逐帧 s3fd 全分辨率人脸检测 | **用 `--box` 固定人脸框**：同片段 4.7s（快约 70 倍），且保持全分辨率 |
| 用了 MPS 反而更慢（6min） | 小模型逐帧搬到 MPS 的开销大于收益 | 用 CPU；只把「人脸检测固定框」当提速手段 |
| 想更快但能接受降分辨率 | — | `--resize_factor 2`：约 5.6 倍提速，整段降到 384×576，放大回 1080 会糊，不推荐 |
| 权重下载 502 / 极慢 | huggingface 直连受限 | 用 `hf-mirror.com`：`camenduru/Wav2Lip`（wav2lip_gan.pth）、`rippertnt/wav2lip`（s3fd.pth） |

## 合成

| 现象 | 原因 | 解法 |
| --- | --- | --- |
| `shutil.rmtree` 被安全策略拦截 | 沙箱禁止递归删除 | 不删目录，改用 UUID 命名的新目录（`/tmp/gxjj/run_<uuid>`） |
| 弹窗压住人物脸 | 弹窗太高或 y 过大 | 脚本已做：底边 >655 自动上移；行高 100、宽 872 |
| 信息卡叠字/断线 | 手绘渐变线首尾亮度不一致 | 用 numpy 生成 sin 渐变遮罩，再一次性贴一条 2px 线 |
| 逐条弹出的行有半透明残影 | 淡入时间过长 | 缩短淡入到 0.14s、放大回弹用 easeOutBack(2.6) |
| 弹窗在深色场景里「糊」成一团 | 面板与背景同色 | 加金色描边 + 双层呼吸光晕；必要时加 `top` 高光 |

## 配音与时间对齐

| 现象 | 原因 | 解法 |
| --- | --- | --- |
| edge-tts 不返回词级时间戳（0 个 WordBoundary） | 该端点对中文不返回 | 用「术语在句中的加权字符位置（标点权重 2.0）× 语音净时长」估算，误差 <0.3s |
| 配音输出为空文件 | macOS `say` 多数中文音色不可用 | 改用 edge-tts；不要用 `say` |
| 某段配音缺字/念错生僻字 | 神经网络音色偶发 | 改写台词绕开生僻字，或换音色重生成 |

## 其他

- 临时目录与缓存：`/tmp/gxjj`（配音/对口型缓存按内容哈希复用）、`/tmp/gxjj/run_*`（每帧序列）。
- 改台词后重跑：只有变化的段落会重新配音与对口型，其余命中缓存。
- 抖音发布：后台勾选「内容由 AI 生成」声明；古籍来源与干支数据发布前人工核对一次。
