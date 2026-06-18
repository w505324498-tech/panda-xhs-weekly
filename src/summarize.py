"""Call DeepSeek API to generate XHS/Douyin content creation analysis."""

from __future__ import annotations

import json
import logging
import os

logger = logging.getLogger(__name__)

API_KEY = os.getenv("DEEPSEEK_API_KEY", "").strip()
BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "").strip() or "https://api.deepseek.com"
MODEL = os.getenv("DEEPSEEK_MODEL", "").strip() or "deepseek-chat"

REQUEST_TIMEOUT = 120


def _parse_json(raw: str) -> any:
    """Parse JSON from LLM response, handling markdown code fences."""
    import re
    text = raw.strip()
    # Strip markdown code fences (```json ... ``` or ``` ... ```)
    m = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if m:
        text = m.group(1).strip()
    return json.loads(text)

AUDIENCE_TAGS = ["AI爱好者", "上班族", "内容创作者", "开发者"]


def _client():
    """Lazy-init the OpenAI client."""
    from openai import OpenAI
    return OpenAI(api_key=API_KEY, base_url=BASE_URL, timeout=REQUEST_TIMEOUT)


def is_available() -> bool:
    return bool(API_KEY)


def _chat(prompt: str, max_tokens: int = 4000) -> str:
    """Send a chat completion request and return the content."""
    client = _client()
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=max_tokens,
        temperature=0.3,
    )
    return resp.choices[0].message.content or ""


# ── GitHub Analysis + Best Topic Picker ──────────────────────────────


def analyze_github_and_pick_best(projects: list[dict]) -> tuple[list[dict], dict]:
    """Analyze GitHub projects for XHS/Douyin content creation and pick the best topic.

    Returns (analyzed_projects, best_topic).
    """
    best_topic: dict = {
        "recommendation_score": 0,
        "recommendation_reason": "",
        "recommended_platform": "",
        "suggested_titles": [],
    }

    if not projects or not is_available():
        for p in projects:
            _fallback_project(p)
        best_topic["recommendation_reason"] = "AI 摘要功能暂不可用，请配置 DEEPSEEK_API_KEY"
        return projects, best_topic

    projects_text = "\n\n".join(
        f"[{i+1}] {p['name']}\nStars: {p['stars']}\nLanguage: {p['language']}\n"
        f"Description: {p['description']}\nKeyword: {p['keyword']}"
        for i, p in enumerate(projects)
    )

    prompt = (
        "你是一个小红书/抖音AI内容创作顾问。你的读者是普通中国人，不是程序员。\n\n"
        "## 核心任务\n"
        "分析以下GitHub AI项目，把每个项目翻译成「小白都能看懂的介绍」，并给出可直接用于内容创作的素材。\n\n"
        "## 输出语言要求\n"
        "- 全部使用中文，禁止出现英文单词（项目名除外）\n"
        "- 用生活化的比喻解释技术概念\n"
        "- 避免术语：API、CLI、deploy、framework、pipeline 等，如果必须出现要翻译成中文\n\n"
        "## 评分标准（内容创作价值）\n"
        "- 小红书（1-5）：有好看的界面/可视化效果吗？能做出吸引人的图文笔记吗？\n"
        "- 抖音（1-5）：操作可录屏演示吗？有视觉冲击力吗？\n"
        "- 公众号（1-5）：有深度解读价值吗？能写成技术科普长文吗？\n\n"
        f"## 本周GitHub AI项目（共{len(projects)}个）\n{projects_text}\n\n"
        "## 输出JSON格式（仅输出JSON，不要其他文字）\n"
        '{"projects":[{"index":1,"one_liner":"一句话中文介绍，15字以内","what_is_it":"通俗解释，50字以内",'
        '"why_notable":["原因1","原因2","原因3"],"content_scores":{"xhs":4,"douyin":3,"gzh":5},'
        '"audience":["AI爱好者"],"xhs_core_hook":"1句话核心卖点，20字以内",'
        '"xhs_titles":["标题1","标题2","标题3"]}],'
        '"best_topic":{"project_index":1,"recommendation_score":5,"recommendation_reason":"一句话推荐理由",'
        '"recommended_platform":"小红书","suggested_titles":["标题1","标题2","标题3"]}}\n\n'
        "## 最佳选题筛选优先级\n"
        "高优先级：Claude Code / Codex / MCP / AI Agent / AI办公 / AI自动化 / 效率工具 / 可录屏演示\n"
        "低优先级：纯SDK / Framework / Library / 纯开发工具"
    )

    try:
        raw = _chat(prompt, max_tokens=4000)
        logger.info("GitHub analysis generated")
        data = _parse_json(raw)

        for item in data.get("projects", []):
            idx = item["index"] - 1
            if 0 <= idx < len(projects):
                projects[idx]["one_liner"] = item.get("one_liner", "")
                projects[idx]["what_is_it"] = item.get("what_is_it", "")
                projects[idx]["why_notable"] = item.get("why_notable", [])[:3]
                projects[idx]["content_scores"] = item.get("content_scores", {"xhs": 0, "douyin": 0, "gzh": 0})
                audience = item.get("audience", [])
                projects[idx]["audience"] = [t for t in audience if t in AUDIENCE_TAGS]
                projects[idx]["xhs_core_hook"] = item.get("xhs_core_hook", "")
                projects[idx]["xhs_titles"] = item.get("xhs_titles", [])[:3]

        bt = data.get("best_topic", {})
        best_topic = {
            "recommendation_score": int(bt.get("recommendation_score", 0)),
            "recommendation_reason": bt.get("recommendation_reason", ""),
            "recommended_platform": bt.get("recommended_platform", ""),
            "suggested_titles": bt.get("suggested_titles", [])[:3],
            "project_index": int(bt.get("project_index", 1)) - 1,
        }
        pi = best_topic["project_index"]
        if 0 <= pi < len(projects):
            best_topic["repo"] = projects[pi]["name"]
            best_topic["repo_url"] = projects[pi]["url"]
        elif projects:
            best_topic["repo"] = projects[0]["name"]
            best_topic["repo_url"] = projects[0]["url"]

    except Exception as e:
        logger.warning("Analysis failed: %s", e)
        for p in projects:
            _fallback_project(p)

    return projects, best_topic


def _fallback_project(p: dict) -> None:
    p.setdefault("one_liner", (p.get("description") or "")[:80])
    p.setdefault("what_is_it", (p.get("description") or "")[:80])
    p.setdefault("why_notable", ["值得关注的AI开源项目"])
    p.setdefault("content_scores", {"xhs": 0, "douyin": 0, "gzh": 0})
    p.setdefault("audience", [])
    p.setdefault("xhs_core_hook", "")
    p.setdefault("xhs_titles", [])


# ── XHS Draft Generator ──────────────────────────────────────────────


def generate_xhs_draft(best_project: dict) -> dict:
    """Generate a full, ready-to-publish Xiaohongshu draft."""
    if not best_project or not is_available():
        return {}

    proj_info = (
        f"项目名：{best_project.get('name', '')}\n"
        f"Stars：{best_project.get('stars', 0)}\n"
        f"描述：{best_project.get('description', '')}\n"
        f"AI分析的一句话介绍：{best_project.get('one_liner', '')}\n"
        f"AI分析的通俗解释：{best_project.get('what_is_it', '')}"
    )

    prompt = (
        "你是一个小红书AI内容博主，擅长用普通人视角分享AI工具。生成一篇可直接发布的小红书草稿。\n\n"
        f"## 项目信息\n{proj_info}\n\n"
        "## 输出JSON（仅JSON）：\n"
        '{"xhs_titles":["标题1-5"],"xhs_body":"300-500字正文",'
        '"cover_texts":["封面文案1-3"],"screenshots":["截图建议1-3"],'
        '"publish_checklist":"发布前检查清单"}\n\n'
        "## 标题要求（5个）\n"
        "- 普通人能看懂，一眼就知道这工具能干嘛\n"
        "- 不要营销号风格（❌「震惊！」「全网首发」）\n"
        "- 每标题20字以内，含emoji\n\n"
        "## 正文要求（300-500字）\n"
        "- 第一人称，像一个普通上班族在分享日常发现\n"
        "- 不像广告，不像AI生成，语气自然口语化\n"
        "- 结构：发现场景 → 工具介绍（大白话） → 为什么值得关注 → 后续计划\n\n"
        "## ⚠️ 人设约束\n"
        "博主只是发现了这个项目，尚未实际使用。只能使用：\n"
        "✅「我发现」「最近注意到」「准备试试看」「看起来」「先马住」\n"
        "❌「我测试过」「我用了」「亲测」「实测」\n\n"
        "## 封面文案（3个，每条10字以内）\n"
        "- 简短有冲击力，适合做封面大字\n\n"
        "JSON 必须完整闭合"
    )

    try:
        raw = _chat(prompt, max_tokens=2500)
        logger.info("XHS draft generated")
        data = _parse_json(raw)
        return {
            "project_name": best_project.get("name", ""),
            "one_liner": best_project.get("one_liner", ""),
            "why_notable": best_project.get("why_notable", []),
            "xhs_titles": data.get("xhs_titles", [])[:5],
            "xhs_body": data.get("xhs_body", ""),
            "cover_texts": data.get("cover_texts", [])[:3],
            "screenshots": data.get("screenshots", [])[:3],
            "publish_checklist": data.get("publish_checklist", ""),
        }
    except Exception as e:
        logger.warning("XHS draft failed: %s", e)
        return {}


# ── Douyin Script Generator ──────────────────────────────────────────


def generate_douyin_script(best_project: dict) -> dict:
    """Generate a Douyin (TikTok) video shooting script outline."""
    if not best_project or not is_available():
        return {}

    proj_info = (
        f"项目名：{best_project.get('name', '')}\n"
        f"Stars：{best_project.get('stars', 0)}\n"
        f"一句话介绍：{best_project.get('one_liner', '')}\n"
        f"通俗解释：{best_project.get('what_is_it', '')}"
    )

    prompt = (
        "你是一个抖音AI内容博主。为以下GitHub项目生成一个抖音视频拍摄脚本大纲。\n\n"
        f"## 项目信息\n{proj_info}\n\n"
        "## 视频要求\n"
        "- 时长：30-60秒\n"
        "- 风格：快节奏、信息密度高\n"
        "- 目标：让观众觉得「这个工具好有用」\n\n"
        "## 输出JSON（仅JSON）：\n"
        '{"video_title":"抖音视频标题（15字以内，吸引人）",'
        '"hook":"开头3秒抓人话术（10字以内）",'
        '"script_outline":["镜头1：...","镜头2：...","镜头3：...","镜头4：...","镜头5：..."],'
        '"caption":"抖音文案（50字以内，带#话题标签）",'
        '"bgm_suggestion":"背景音乐风格建议"}\n\n'
        "## 人设约束\n"
        "博主只是在介绍自己发现的项目，不是专家。使用「发现」「分享」「看起来不错」等语气。\n"
        "JSON 必须完整闭合"
    )

    try:
        raw = _chat(prompt, max_tokens=1500)
        logger.info("Douyin script generated")
        data = _parse_json(raw)
        return {
            "video_title": data.get("video_title", ""),
            "hook": data.get("hook", ""),
            "script_outline": data.get("script_outline", [])[:5],
            "caption": data.get("caption", ""),
            "bgm_suggestion": data.get("bgm_suggestion", ""),
        }
    except Exception as e:
        logger.warning("Douyin script failed: %s", e)
        return {}
