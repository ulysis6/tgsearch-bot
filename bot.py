#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tgsearch_nav_bot — 稳妥版 + 双语 + 可点击分类按钮"""
import json, logging, os, re, random
from collections import defaultdict
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, filters, ContextTypes)

token = os.environ.get("TG_TOKEN", "")
RESOURCES_FILE = "resources.json"
BOT_USERNAME = "tgsearch_nav_all_bot"

with open(RESOURCES_FILE, "r", encoding="utf-8") as f:
    RESOURCES = json.load(f)

CATEGORIES = list(RESOURCES.keys())
CATEGORY_EMOJIS = {"电子书资源":"📚","学习资源":"🎓","设计素材":"🎨","软件工具":"💻","AI工具":"🤖","效率模板":"📋","搞钱/副业资源":"💰"}
CATEGORY_EN = {"电子书资源":"E-books","学习资源":"Learning","设计素材":"Design","软件工具":"Software","AI工具":"AI Tools","效率模板":"Templates","搞钱/副业资源":"Money"}

SEARCH_INDEX = []
for cat, items in RESOURCES.items():
    for item in items:
        SEARCH_INDEX.append({**item, "category": cat,
            "_search_text": f"{item['name']} {item['desc']} {' '.join(item['tags'])} {cat}".lower()})

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

def _(zh, en):
    return f"{zh}\n💬 {en}"

def search_resources(query, max_results=8):
    q = query.lower()
    terms = [t.strip() for t in re.split(r'[\s,，、]+', q) if t.strip()]
    if not terms: return []
    return [item for item in SEARCH_INDEX if all(t in item["_search_text"] for t in terms)][:max_results]

def get_emoji(cat): return CATEGORY_EMOJIS.get(cat, "📁")

def build_categories_kb():
    """生成可点击的分类按钮键盘"""
    buttons = []
    for cat in CATEGORIES:
        emoji = get_emoji(cat)
        en = CATEGORY_EN.get(cat, "")
        count = len(RESOURCES[cat])
        label = f"{emoji} {cat} ({count})"
        buttons.append([InlineKeyboardButton(label, callback_data=f"cat:{cat}")])
    return buttons

async def start(update, context):
    msg = _(
        "👋 欢迎使用 **TG Search**！\n\n"
        "我是免费资源 + AI工具导航助手\n"
        "直接输入关键词就能搜索\n\n"
        "📌 **可用命令**\n"
        "/search <关键词> — 搜索\n"
        "/categories — 所有分类（可点击）\n"
        "/daily — 每日推荐\n"
        "/help — 帮助",
        "👋 Welcome to **TG Search**!\n\n"
        "Free Resources + AI Tools Navigator\n"
        "Just type keywords to search\n\n"
        "📌 **Commands**\n"
        "/search <keyword> — Search\n"
        "/categories — Browse (clickable)\n"
        "/daily — Daily pick\n"
        "/help — Help"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")

async def help_cmd(update, context):
    msg = _(
        "📖 **使用帮助**\n\n"
        "🔍 /search 关键词 — 搜索\n"
        "📂 /categories — 点击分类浏览\n"
        "⭐ /daily — 每日推荐\n"
        "📝 /submit 名称:简介:链接 — 投稿\n\n"
        "💡 或直接输入文字自动搜索",
        "📖 **Help**\n\n"
        "🔍 /search keyword — Search\n"
        "📂 /categories — Tap to browse\n"
        "⭐ /daily — Daily recommendation\n"
        "📝 /submit Name:Desc:URL — Submit\n\n"
        "💡 Or just type to search"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")

async def categories(update, context):
    buttons = build_categories_kb()
    msg = _(
        "📂 **资源分类**\n\n👇 点击分类查看资源",
        "📂 **Categories**\n\n👇 Tap a category to browse"
    )
    await update.message.reply_text(msg, parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(buttons))

async def search(update, context):
    text = update.message.text.strip()
    query = text.replace("/search", "", 1).strip() if text.startswith("/search") else text

    if not query or len(query) < 2:
        await update.message.reply_text(_(
            "🔍 请输入关键词\n例如 /search 翻译 或直接发送「翻译」",
            "🔍 Enter keywords\nE.g. /search translate or just type 'translate'"
        )); return

    results = search_resources(query)
    if not results:
        await update.message.reply_text(_(
            f"😅 没找到「{query}」相关的资源\n试试其他关键词或用 /categories 分类浏览",
            f"😅 No results for \"{query}\"\nTry different keywords or use /categories"
        )); return

    grouped = defaultdict(list)
    for r in results: grouped[r["category"]].append(r)

    msg = _(
        f"🔍 **「{query}」结果（{len(results)} 条）**\n\n",
        f"🔍 **{query}** ({len(results)} results)\n\n"
    )
    for cat, items in grouped.items():
        for item in items:
            msg += f"  • [{item['name']}]({item['url']}) — {item['desc'][:50]}\n"
        msg += "\n"
    await update.message.reply_text(msg, parse_mode="Markdown", disable_web_page_preview=True)

async def daily(update, context):
    cat = random.choice(CATEGORIES)
    item = random.choice(RESOURCES[cat])
    msg = _("⭐ **今日推荐 / Daily Pick**\n\n", "⭐ **Daily Pick**\n\n")
    msg += f"{get_emoji(cat)} **{item['name']}**\n"
    msg += f"   {item['desc']}\n"
    msg += f"   🔗 {item['url']}\n"
    msg += f"   📂 {cat} — {CATEGORY_EN.get(cat, '')}"
    await update.message.reply_text(msg, parse_mode="Markdown")

async def submit(update, context):
    text = update.message.text.replace("/submit", "", 1).strip()
    if not text or ":" not in text:
        await update.message.reply_text(_(
            "📝 **投稿格式 / Format:**\n/submit 名称:简介:链接\n例: /submit Notion AI:AI笔记:https://notion.so",
            "📝 **Format:**\n/submit Name:Desc:URL\n/submit Notion AI:AI Notes:https://notion.so"
        )); return
    parts = text.split(":", 2)
    if len(parts) < 3:
        await update.message.reply_text(_("格式不对 / Invalid format")); return
    name, desc, url = [p.strip() for p in parts]
    logger.info(f"投稿: {name}")
    await update.message.reply_text(_(
        f"✅ 收到「{name}」！审核后收录 🎉",
        f"✅ Thanks! We'll review and add \"{name}\" 🎉"
    ))

async def text_handler(update, context):
    text = update.message.text.strip()
    if len(text) < 2: return
    if update.message.chat.type in ("group", "supergroup"):
        if BOT_USERNAME.lower() not in text.lower(): return
        text = re.sub(r'@\w+', '', text).strip()  # 去掉 @botusername
    await search(update, context)

async def button_handler(update, context):
    """处理分类按钮点击"""
    try:
        q = update.callback_query
        await q.answer()

        if q.data.startswith("cat:"):
            cat_name = q.data.split(":", 1)[1]
            if cat_name not in RESOURCES: return

            items = RESOURCES[cat_name]
            emoji = get_emoji(cat_name)
            en = CATEGORY_EN.get(cat_name, "")
            # 只显示前10条
            msg = f"{emoji} **{cat_name}** ({len(items)}) — {en}\n\n"
            for i, item in enumerate(items[:10], 1):
                msg += f"{i}. [{item['name']}]({item['url']})\n"
                msg += f"   {item['desc'][:60]}\n\n"

            # 剩下的提示
            if len(items) > 10:
                msg += _(
                    f"...还有 {len(items)-10} 条，用 /search 搜索更多",
                    f"...{len(items)-10} more, use /search"
                )

            # 加返回按钮
            back_btn = [[InlineKeyboardButton("📂 Back", callback_data="back_cats")]]
            await q.edit_message_text(msg, parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(back_btn), disable_web_page_preview=True)
            return

        if q.data == "back_cats":
            buttons = build_categories_kb()
            msg = _(
                "📂 **资源分类**\n\n👇 点击分类查看资源",
                "📂 **Categories**\n\n👇 Tap a category to browse"
            )
            await q.edit_message_text(msg, parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(buttons))
            return

    except Exception as e:
        logger.error(f"button_handler error: {e}")

async def error_handler(update, context):
    logger.error(f"Error: {context.error}")

def main():
    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("categories", categories))
    app.add_handler(CommandHandler("search", search))
    app.add_handler(CommandHandler("daily", daily))
    app.add_handler(CommandHandler("submit", submit))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_error_handler(error_handler)
    print("tgsearch stable started...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
