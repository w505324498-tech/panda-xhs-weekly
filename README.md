# 🎬 Panda XHS Weekly

每周一自动抓取 GitHub AI 热门项目，调用 DeepSeek API 分析内容创作价值，生成小红书/抖音选题并邮件推送。

## 功能

- 🤖 **GitHub AI 热门** — 10 个关键词 × GitHub Search API，每周抓取 Top 10 项目
- 🧠 **DeepSeek 内容分析** — 每个项目评分（小红书/抖音/公众号），标注目标受众
- 🏆 **最佳选题推荐** — AI 挑选最适合做内容的项目 + 建议标题
- 📕 **小红书完整草稿** — 可直接复制的正文、5 选 1 标题、封面文案、配图建议
- 🎬 **抖音拍摄脚本** — 30-60 秒视频大纲、开头话术、文案、BGM 建议
- 📧 **邮件推送** — 每周一早上 8:00 自动发送

## 快速开始

```bash
git clone https://github.com/w505324498/panda-xhs-weekly.git
cd panda-xhs-weekly
pip install -r requirements.txt
cp .env.example .env
# 编辑 .env 填入 API Key
python -m src.main
```

## 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `DEEPSEEK_API_KEY` | DeepSeek API Key | — |
| `DEEPSEEK_BASE_URL` | API 地址 | `https://api.deepseek.com` |
| `DEEPSEEK_MODEL` | 模型名 | `deepseek-chat` |
| `GITHUB_TOKEN` | GitHub Token（提高限额） | 空 |
| `SMTP_HOST/PORT/USER/PASS` | SMTP 配置 | — |
| `MAIL_TO/FROM` | 收件/发件人 | — |

> 不配置 `DEEPSEEK_API_KEY` 也能运行，会收到原始项目列表（无 AI 分析）。

## GitHub Actions 定时

每周一 UTC 00:00（北京时间 8:00）自动运行。需配置 GitHub Secrets：

```
DEEPSEEK_API_KEY, GITHUB_TOKEN, SMTP_HOST, SMTP_PORT,
SMTP_USER, SMTP_PASS, MAIL_TO, MAIL_FROM
```

## 搜索关键词

`config/sources.yaml` 中配置 10 个 GitHub 搜索关键词：ai-agent、mcp-server、claude-code、codex、llm-tools、prompt-engineering、ai-automation、ai-video、ai-image、ai-writing

## 相关项目

- 📰 [panda-news-daily](https://github.com/w505324498/panda-intelligence-center) — 每日全球新闻中文摘要
