"""Panda XHS Weekly — Weekly GitHub AI projects → XHS/Douyin content.

Orchestrates: GitHub trending → AI content analysis → XHS draft + Douyin script → Email.
Runs every Monday 8:00 AM Beijing time.
"""

import logging
import os
import sys
from datetime import date
from pathlib import Path

# Load .env file
_dotenv_path = Path(__file__).resolve().parent.parent / ".env"
if _dotenv_path.exists():
    with open(_dotenv_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip())

from src.fetch_github import fetch_github_projects
from src.summarize import (
    analyze_github_and_pick_best,
    generate_douyin_script,
    generate_xhs_draft,
    is_available as ai_available,
)
from src.mailer import send_weekly_email

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("panda-xhs")


def main():
    date_str = date.today().isoformat()
    errors: list[str] = []

    # ── 1. Fetch GitHub AI Projects ──────────────────────────────────
    logger.info("══ Step 1/4: Fetching GitHub AI projects…")
    projects: list[dict] = []
    try:
        projects = fetch_github_projects()
        logger.info("  Projects: %d", len(projects))
    except Exception as e:
        logger.exception("GitHub fetch crashed")
        errors.append(f"GitHub 数据获取失败: {e}")

    # ── 2. AI Content Analysis ───────────────────────────────────────
    best_topic: dict = {}
    if ai_available() and projects:
        logger.info("══ Step 2/4: AI content analysis + best topic…")
        try:
            projects, best_topic = analyze_github_and_pick_best(projects)
        except Exception as e:
            logger.exception("Analysis crashed")
            errors.append(f"AI 分析失败: {e}")
    else:
        logger.info("══ Step 2/4: AI analysis SKIPPED (DEEPSEEK_API_KEY not set or no projects)")
        errors.append("⚠️ DEEPSEEK_API_KEY 未配置或无项目数据")

    # ── 3. Generate Drafts ───────────────────────────────────────────
    xhs_draft: dict = {}
    douyin_script: dict = {}

    if ai_available() and projects:
        logger.info("══ Step 3/4: Generating XHS draft + Douyin script…")
        # Find best project
        best_idx = best_topic.get("project_index", 0)
        best_proj = projects[best_idx] if 0 <= best_idx < len(projects) else projects[0]

        try:
            xhs_draft = generate_xhs_draft(best_proj)
        except Exception as e:
            logger.exception("XHS draft crashed")
            errors.append(f"小红书草稿生成失败: {e}")
        try:
            douyin_script = generate_douyin_script(best_proj)
        except Exception as e:
            logger.exception("Douyin script crashed")
            errors.append(f"抖音脚本生成失败: {e}")
    else:
        logger.info("══ Step 3/4: Draft generation SKIPPED")

    # ── 4. Send Email ────────────────────────────────────────────────
    logger.info("══ Step 4/4: Sending email…")
    try:
        ok = send_weekly_email(
            date_str=date_str,
            projects=projects,
            best_topic=best_topic,
            xhs_draft=xhs_draft,
            douyin_script=douyin_script,
            errors=errors if errors else None,
        )
        if ok:
            logger.info("✅ Email sent successfully!")
        else:
            logger.error("❌ Email sending failed — check SMTP config.")
            sys.exit(1)
    except Exception as e:
        logger.exception("Mailer crashed")
        sys.exit(1)

    logger.info("══ Done: Projects=%d, Errors=%d ══", len(projects), len(errors))


if __name__ == "__main__":
    main()
