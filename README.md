# lenmu-video — Lenmu MCP 總導演 Skill

讓 AI 代理（Claude、Codex 等支援 Agent Skills 的工具）在 [Lenmu](https://lenmu.ai) 上當一支 AI 短片的總導演：從故事、分鏡、配色、首尾幀、審核、生成，到用程式做後製，一路把錯誤擋在花錢之前。

An Agent Skill (works with Claude and OpenAI Codex) that makes your agent the director of an AI short film on the Lenmu MCP: story → storyboard → palette → first/last frames → independent review → generation → code-based post, catching mistakes before money is spent.

## 核心做法 / How it works

- **分工**：AI 代理寫故事、分鏡、提示詞並檢查每張圖和每段影片；Lenmu 的 Seedream 畫圖、Seedance／OmniHuman 做動態；使用者只負責選方向、確認畫風、批准花錢、看動態、聽聲音。
- **五道關卡**：故事確認前不畫圖；畫風確認前不畫正式鏡頭；每鏡送影片前由另一個 agent 只讀審核，通過後報價、同意才送；影片有問題先用程式修，修不了只重拍那一鏡；交片前抽查剪接點前後 3 幀。
- **誠實**：AI 代理看不到真正的動態、聽不到聲音，沒看過的東西會明確告訴你。
- **不覆蓋、不刪除**：每個新版本都存新檔。不儲值，餘額不足就停下來先粗剪。

## 內容 / What's inside

```
skills/lenmu-video/
  SKILL.md                 完整流程
  scripts/colorboard.py    色塊草圖總表（彩色＋黑白）與明暗對比檢查
  scripts/framecheck.py    首尾幀疊圖、差異熱圖、手機尺寸預覽、放大切格
  scripts/micromosaic.py   眼嘴微馬賽克（只限 AI 生成的虛構人物，不可用於真人照片）
.claude-plugin/            Claude Code plugin marketplace 設定
.github/workflows/         推 v* tag 時自動打包 lenmu-video.zip 並發 Release
```

## 安裝 / Install

### 第 1 步：連上 Lenmu MCP

MCP 網址：`https://lenmu.ai/mcp`

| 平台 | 做法 |
|---|---|
| **Claude.ai／Claude 桌面版** | 設定 → Connectors → 新增自訂 connector，網址填 `https://lenmu.ai/mcp`，登入 Lenmu 帳號 |
| **Claude Code** | `claude mcp add --transport http lenmu https://lenmu.ai/mcp` |
| **OpenAI Codex**（CLI、IDE、App） | 在 `~/.codex/config.toml` 加入下面設定，再執行 `codex mcp login lenmu` 登入 |

```toml
[mcp_servers.lenmu]
url = "https://lenmu.ai/mcp"
```

### 第 2 步：安裝 skill（擇一）

**A. 一行指令，支援 Claude Code、Codex、Cursor 等多種代理**
```bash
npx skills add chesterkuo/lenmu-ai
```

**B. Claude Code plugin（之後可以自動更新）**
```
/plugin marketplace add chesterkuo/lenmu-ai
/plugin install lenmu-video@lenmu-skills
```

**C. Codex 內建安裝器**：在 Codex 裡輸入
```
$skill-installer https://github.com/chesterkuo/lenmu-ai/tree/main/skills/lenmu-video
```

**D. Claude.ai／Claude 桌面版**：下載 [`lenmu-video.zip`](https://github.com/chesterkuo/lenmu-ai/releases/latest/download/lenmu-video.zip)（或到 [Releases](https://github.com/chesterkuo/lenmu-ai/releases) 頁面），在 設定 → Capabilities → Skills 上傳。需先在 設定 → Capabilities 開啟「Code execution」。

**E. 手動**
```bash
git clone https://github.com/chesterkuo/lenmu-ai.git
# Claude Code
cp -r lenmu-ai/skills/lenmu-video ~/.claude/skills/
# Codex
cp -r lenmu-ai/skills/lenmu-video ~/.codex/skills/
```
裝好後重開 Claude Code 或 Codex。

### 第 3 步：腳本需要的套件

需要 Python 3 和 `ffmpeg`／`ffprobe`（macOS：`brew install ffmpeg`；Ubuntu：`sudo apt install ffmpeg`）。

```bash
pip install numpy pillow opencv-python   # 配歌卡點另需 librosa
# micromosaic.py 用的 YuNet 人臉偵測模型（MIT License），下載到你做片的工作資料夾
curl -L -o face_detection_yunet_2023mar.onnx \
  https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx
```

缺套件或模型時，代理會在第一步檢查時告訴你，也可以讓它代為安裝。

代理的沙盒要能連到 `lenmu.ai`（下載生成結果、上傳素材用）。連不上時 skill 會改用 Lenmu 內建的剪接，但部分程式後製和檢查會做不到。

## 使用 / Usage

跟你的代理說：「用 Lenmu 幫我做一支短片：〔一句話或初步劇情〕」。它會先問片長、畫幅、總預算、要不要配樂和字幕，再一步步帶你過關卡。

也可以直接叫出 skill：Claude Code 手動安裝用 `/lenmu-video`，plugin 安裝用 `/lenmu-video:lenmu-video`；Codex 用 `$lenmu-video`。

## 注意 / Notes

- 已在 Claude 和 OpenAI Codex 上測試可連上 Lenmu MCP。
- 模型清單與價格會變動，skill 要求每次先呼叫 `list_models`；文件內價格為 2026-11 快照。
- 所有生成都會花 Lenmu 點數，代理會先報價、等你同意才送出。

## 參考 / Credits

- 總導演工作流程（分工、關卡、片段式故事、分鏡構圖、首尾幀檢查、審核、後製規則）改編自 [@eianlu](https://x.com/eianlu) 在 X 上分享的 Seedance 短片導演提示詞，改成 Lenmu MCP 版本。
- 提示詞結構參考：[beshuaxian/higgsfield-seedance2-jineng](https://github.com/beshuaxian/higgsfield-seedance2-jineng)、[dexhunter/seedance2-skill](https://github.com/dexhunter/seedance2-skill)

## License

MIT
