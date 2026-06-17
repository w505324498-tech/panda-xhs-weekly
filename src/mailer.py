"""Send XHS/Douyin weekly content email via SMTP."""

from __future__ import annotations

import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

logger = logging.getLogger(__name__)

SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")
MAIL_TO = os.getenv("MAIL_TO", "")
MAIL_FROM = os.getenv("MAIL_FROM", SMTP_USER)


def send_weekly_email(
    *,
    date_str: str,
    projects: list[dict],
    best_topic: dict,
    xhs_draft: dict,
    douyin_script: dict,
    errors: list[str] | None = None,
) -> bool:
    """Compose and send the weekly XHS/Douyin content email."""
    if not SMTP_HOST or not SMTP_USER or not SMTP_PASS:
        logger.error("SMTP not configured.")
        return False
    if not MAIL_TO:
        logger.error("MAIL_TO not configured.")
        return False

    html = _build_html(
        date_str=date_str, projects=projects, best_topic=best_topic,
        xhs_draft=xhs_draft, douyin_script=douyin_script, errors=errors,
    )

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"🎬 本周AI选题 - {date_str}"
    msg["From"] = MAIL_FROM
    msg["To"] = MAIL_TO
    msg.attach(MIMEText(html, "html", "utf-8"))

    try:
        if SMTP_PORT == 465:
            server = smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=30)
        else:
            server = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30)
            server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.sendmail(MAIL_FROM, [MAIL_TO], msg.as_string())
        server.quit()
        logger.info("Email sent to %s", MAIL_TO)
        return True
    except Exception as e:
        logger.error("SMTP send failed: %s", e)
        return False


def _build_html(
    *,
    date_str: str,
    projects: list[dict],
    best_topic: dict,
    xhs_draft: dict,
    douyin_script: dict,
    errors: list[str] | None = None,
) -> str:
    """Build the XHS/Douyin weekly email."""

    # ── Errors ────────────────────────────────────────────────────────
    errors_html = ""
    if errors:
        errors_html = (
            '<div style="background:#fff3cd; padding:14px; border-radius:8px; margin-bottom:24px; border-left:4px solid #f0a500">'
            + "".join(f"<div style='color:#856404; font-size:13px; margin:4px 0'>⚠️ {_esc(e)}</div>" for e in errors)
            + "</div>"
        )

    # ── Best Topic Card ──────────────────────────────────────────────
    score = best_topic.get("recommendation_score", 0)
    reason = best_topic.get("recommendation_reason", "")
    platform = best_topic.get("recommended_platform", "")
    titles = best_topic.get("suggested_titles", [])
    repo_name = best_topic.get("repo", "")
    repo_url = best_topic.get("repo_url", "")

    rec_stars = "★" * min(score, 5) + "☆" * max(0, 5 - score) if score > 0 else ""
    platform_bg = "#e6005c" if "小红书" in platform else "#010101" if "抖音" in platform else "#8250df"
    platform_badge = (
        f'<span style="display:inline-block; background:{platform_bg}; color:#fff; '
        f'font-size:12px; padding:3px 10px; border-radius:10px; margin-left:8px">{_esc(platform)}</span>'
    ) if platform else ""

    titles_html = ""
    if titles:
        titles_html = '<ol style="margin:8px 0 0 0; padding-left:20px">' + "".join(
            f'<li style="font-size:14px; color:#24292f; margin-bottom:4px">{_esc(t)}</li>'
            for t in titles
        ) + "</ol>"

    best_topic_html = f"""
    <div style="padding:20px; background:linear-gradient(135deg, #fffde7 0%, #fff8e1 100%);
                border:2px solid #f9a825; border-radius:12px; margin-bottom:24px">
      <div style="font-size:18px; font-weight:bold; color:#e65100; margin-bottom:12px">
        🏆 本周最佳选题 {platform_badge}
      </div>
      <div style="font-size:15px; color:#333; margin-bottom:8px">
        推荐指数: <span style="color:#f0a500; font-size:16px">{rec_stars or "—"}</span>
      </div>
      <div style="font-size:14px; color:#555; margin-bottom:12px">{_esc(reason)}</div>
      {f'<div style="font-size:13px; color:#666; margin-bottom:4px">参考项目: <a href="{repo_url}" style="color:#0969da">{_esc(repo_name)}</a></div>' if repo_name else ""}
      <div style="font-size:14px; font-weight:bold; color:#24292f; margin-top:12px; margin-bottom:4px">💬 建议标题</div>
      {titles_html}
    </div>"""

    # ── XHS Draft Section ────────────────────────────────────────────
    xhs_html = ""
    if xhs_draft and xhs_draft.get("xhs_body"):
        titles_html2 = ""
        if xhs_draft.get("xhs_titles"):
            titles_html2 = (
                '<ol style="margin:8px 0; padding-left:20px">' +
                "".join(f'<li style="font-size:14px; color:#24292f; margin-bottom:4px">{_esc(t)}</li>'
                        for t in xhs_draft["xhs_titles"]) + "</ol>"
            )

        why_html = ""
        if xhs_draft.get("why_notable"):
            why_html = (
                '<ul style="margin:4px 0; padding-left:18px; font-size:13px; color:#444">' +
                "".join(f"<li>{_esc(w)}</li>" for w in xhs_draft["why_notable"]) + "</ul>"
            )

        cover_html = ""
        if xhs_draft.get("cover_texts"):
            cover_html = "".join(
                f'<span style="display:inline-block; background:#f0f0f0; padding:3px 10px; '
                f'border-radius:6px; margin:2px 4px 2px 0; font-size:12px">📌 {_esc(c)}</span>'
                for c in xhs_draft["cover_texts"]
            )

        screenshots_html = ""
        if xhs_draft.get("screenshots"):
            screenshots_html = (
                '<ul style="margin:4px 0; padding-left:18px; font-size:13px; color:#555">' +
                "".join(f"<li>{_esc(s)}</li>" for s in xhs_draft["screenshots"]) + "</ul>"
            )

        checklist = xhs_draft.get("publish_checklist", "")

        xhs_html = f"""
    <h2 style="font-size:20px; color:#e6005c; border-bottom:2px solid #e6005c; padding-bottom:8px; margin-top:32px">
      📕 小红书完整草稿
    </h2>
    <div style="padding:20px; background:#fff5f7; border-radius:12px; margin-bottom:24px">
      <div style="margin-bottom:16px">
        <div style="font-size:18px; font-weight:bold; color:#24292f; margin-bottom:4px">
          📦 {_esc(xhs_draft.get('project_name', ''))}
        </div>
        <div style="font-size:14px; color:#555">{_esc(xhs_draft.get('one_liner', ''))}</div>
      </div>
      <div style="margin-bottom:16px">
        <div style="font-size:14px; font-weight:bold; color:#333; margin-bottom:4px">为什么值得关注：</div>
        {why_html}
      </div>
      <div style="margin-bottom:16px">
        <div style="font-size:15px; font-weight:bold; color:#e6005c; margin-bottom:6px">📝 小红书标题（5选1）</div>
        {titles_html2}
      </div>
      <div style="margin-bottom:20px">
        <div style="font-size:15px; font-weight:bold; color:#e6005c; margin-bottom:8px">📄 正文（可直接复制）</div>
        <div style="font-size:14px; color:#333; line-height:1.9; white-space:pre-wrap;
                    background:#fff; padding:16px; border-radius:8px; border:1px solid #fdd">
{_esc(xhs_draft.get('xhs_body', ''))}</div>
      </div>
      <div style="margin-bottom:16px">
        <div style="font-size:14px; font-weight:bold; color:#333; margin-bottom:4px">🎨 封面文案</div>
        {cover_html}
      </div>
      <div style="margin-bottom:16px">
        <div style="font-size:14px; font-weight:bold; color:#333; margin-bottom:4px">📸 推荐配图</div>
        {screenshots_html}
      </div>
      <div style="margin-bottom:8px">
        <div style="font-size:14px; font-weight:bold; color:#333; margin-bottom:4px">✅ 发布前检查</div>
        <div style="font-size:13px; color:#444; background:#f6f8fa; padding:10px 12px; border-radius:6px; line-height:1.8">{_esc(checklist)}</div>
      </div>
    </div>"""

    # ── Douyin Script Section ────────────────────────────────────────
    douyin_html = ""
    if douyin_script and douyin_script.get("video_title"):
        outline = douyin_script.get("script_outline", [])
        outline_html = "".join(
            f'<li style="margin-bottom:6px; font-size:14px">{_esc(s)}</li>'
            for s in outline
        ) if outline else ""

        douyin_html = f"""
    <h2 style="font-size:20px; color:#010101; border-bottom:2px solid #010101; padding-bottom:8px; margin-top:32px">
      🎬 抖音拍摄脚本
    </h2>
    <div style="padding:20px; background:#f9f9f9; border-radius:12px; margin-bottom:24px">
      <div style="font-size:17px; font-weight:bold; color:#010101; margin-bottom:8px">
        🎵 {_esc(douyin_script.get('video_title', ''))}
      </div>
      <div style="font-size:15px; color:#e6005c; margin-bottom:12px; font-weight:bold">
        🎯 开头3秒: {_esc(douyin_script.get('hook', ''))}
      </div>
      <div style="font-size:14px; font-weight:bold; color:#333; margin-bottom:8px">📋 脚本大纲</div>
      <ol style="padding-left:20px; color:#333">{outline_html}</ol>
      <div style="margin-top:12px; padding:10px; background:#fff; border-radius:6px; font-size:14px; color:#555">
        <strong>📝 文案:</strong> {_esc(douyin_script.get('caption', ''))}
      </div>
      <div style="margin-top:8px; font-size:13px; color:#888">
        🎶 BGM建议: {_esc(douyin_script.get('bgm_suggestion', ''))}
      </div>
    </div>"""

    # ── Project Table ────────────────────────────────────────────────
    def _project_row(p: dict) -> str:
        scores = p.get("content_scores", {})
        xhs = scores.get("xhs", 0)
        dy = scores.get("douyin", 0)
        return f"""
        <tr>
          <td style="padding:12px; border-bottom:1px solid #eee; font-size:14px">
            <a href="{p.get('url', '')}" style="color:#0969da; text-decoration:none; font-weight:bold">{_esc(p.get('name', ''))}</a>
            <span style="color:#666; margin-left:6px">⭐{p.get('stars', 0)}</span>
          </td>
          <td style="padding:12px; border-bottom:1px solid #eee; font-size:13px">
            📕{'★'*xhs}{'☆'*(5-xhs)} 🎵{'★'*dy}{'☆'*(5-dy)}
          </td>
          <td style="padding:12px; border-bottom:1px solid #eee; font-size:13px; color:#555">
            {_esc(p.get('one_liner', '')[:40])}
          </td>
        </tr>"""

    project_rows = "".join(_project_row(p) for p in projects[:10]) if projects else (
        "<tr><td colspan='3' style='padding:16px; color:#999'>暂无数据</td></tr>"
    )

    return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"></head>
<body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
             max-width:640px; margin:0 auto; padding:20px; background:#f6f8fa">
  <div style="background:#fff; border-radius:12px; padding:28px; box-shadow:0 2px 8px rgba(0,0,0,0.06)">

    <!-- Header -->
    <div style="text-align:center; padding-bottom:20px; border-bottom:3px solid #e6005c; margin-bottom:24px">
      <h1 style="font-size:24px; color:#24292f; margin:0 0 6px 0">🎬 Panda XHS Weekly</h1>
      <p style="font-size:14px; color:#656d76; margin:0">{date_str} · 本周AI选题</p>
    </div>

    {errors_html}
    {best_topic_html}
    {xhs_html}
    {douyin_html}

    <!-- Project Rankings -->
    <h2 style="font-size:19px; color:#8250df; border-bottom:2px solid #8250df; padding-bottom:8px; margin-top:32px">
      📊 本周 GitHub AI 热门项目 Top 10
    </h2>
    <table style="width:100%; border-collapse:collapse; margin-bottom:8px">
      <tr style="background:#f6f8fa; font-size:12px; color:#666; text-align:left">
        <th style="padding:10px">项目</th>
        <th style="padding:10px">内容评分</th>
        <th style="padding:10px">一句话</th>
      </tr>
      {project_rows}
    </table>

    <!-- Footer -->
    <div style="margin-top:32px; padding-top:16px; border-top:1px solid #e8e8e8;
                font-size:12px; color:#999; text-align:center">
      🐼 Panda XHS Weekly · Every Monday · Powered by DeepSeek
    </div>
  </div>
</body>
</html>"""


def _esc(s: str) -> str:
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
