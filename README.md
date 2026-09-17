# 千川短视频全链路自动化剪辑系统 (for Codex)

专注于**巨量千川与短视频投流广告**的自动化剪辑套件。集成“纯人话文案策划、MiniMax 专属投流配音、Whisper 词级时间戳对齐、68px 固定大字号零压缩排版、App 录屏视听语义咬合、FFmpeg 混音出片”全链路。

---

## 🚀 极速上手 (Codex 环境)

### 1. 环境准备
确保电脑已安装 `ffmpeg` 和 Python 3.10+：
```bash
pip install -r requirements.txt
```

### 2. 配置 MiniMax 配音密钥
复制 `.env.example` 为 `.env`，填入你的 MiniMax API Key：
```bash
MINIMAX_API_KEY=你的MiniMax_API_KEY
```
*(注：如果你的本地已部署过 MiniMax 音色库，脚本会自动检测并无缝调用)*

---

## 🤖 在 Codex 中如何使用？

直接把当前文件夹作为项目根目录在 Codex（或 VS Code Codex 插件）中打开。

### 方式一：直接对 Codex 下达自然语言指令 (推荐)
由于项目根目录已内置 `AGENTS.md` 和 `CODEX.md`，Codex 会自动加载千川角色设定与剪辑铁律。你只需在对话框输入：

> **“帮我给【智能戒指】写一篇突出隐蔽录音和双向翻译的纯人话投流文案，并调用素材库一键剪辑出片。”**

Codex 会自动完成：
1. 输出符合投流黄金标准的纯人话通读文案；
2. 自动调用 `scripts/pipeline.py` 生成配音、对齐字幕并合成成片。

---

### 方式二：终端 CLI 命令行调用

#### 一键全流程直出成片：
```bash
python scripts/pipeline.py \
  --text "写长方案或者复盘总结，最痛苦的就是手指在玻璃屏幕上戳键盘戳得发酸。我现在写东西全靠这根笔。先在屏幕上随手画个逻辑框架，到了要填大段文字的时候，大拇指按住笔身直接开口说，大段文字直接顺畅流进光标里。画提纲、填文字全在一根笔上无缝搞定。脑子里的思路一点都不中断，半小时就把平时半天的工作量给干完了。" \
  --material-dir ./materials \
  --bgm ./bgm/科技与人.mp3 \
  --output ./output/成品视频.mp4
```

#### 分步精细化调试：
```bash
# 1. 单独生成配音
python scripts/tts.py --text "你的文案..." --output ./output/voice.mp3

# 2. 单独对齐字幕（自动切分为 4~8 字短句，无缝消除黑屏）
python scripts/align.py --audio ./output/voice.mp3 --output ./output/subs.json

# 3. 组装画面并混音渲染
python scripts/render.py --audio ./output/voice.mp3 --subs ./output/subs.json --material-dir ./materials --bgm ./bgm/科技与人.mp3 --output ./output/成片.mp4
```

---

## 📐 核心工业铁律 (系统已固化)
1. **文案**：前 1.5 秒必须是生理痛点或产品反差硬钩子，拒绝顺口溜、假大空，突出真实手部动作，坚决不用“外挂”等风控违禁词；
2. **字幕**：锁死 **68px 固定大字号**（亮黄 `#FFE000` + 6px 纯黑硬边 + 阴影），**严控 4~8 字短句**，两侧呼吸留白 $\ge 12\%$，绝不压缩字号；
3. **咬合**：讲到什么功能，画面必须精确展示对应 App 录屏界面（如讲会议纪要必配会议总结，讲健康必配心率血氧）；
4. **音频**：`normalize=0`，目标响度锁定在 **-11.5 LUFS ~ -12.5 LUFS** 黄金听感区。
