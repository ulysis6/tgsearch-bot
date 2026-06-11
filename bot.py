#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tgsearch_nav_bot — 分类按钮 + 分页翻页 + 双语"""
import json, logging, os, re, random
from collections import defaultdict
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, filters, ContextTypes)

token = os.environ.get("TG_TOKEN", "")
RESOURCES_FILE = "resources.json"
BOT_USERNAME = "tgsearch_nav_all_bot"
ITEMS_PER_PAGE = 10

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

def _(zh, en): return f"{zh}\n💬 {en}"
def get_emoji(cat): return CATEGORY_EMOJIS.get(cat, "📁")

def build_menu_kb():
    """首页菜单按钮"""
    btns = []
    for cat in CATEGORIES:
        label = f"{get_emoji(cat)} {cat} - {CATEGORY_EN.get(cat, '')} ({len(RESOURCES[cat])})"
        btns.append([InlineKeyboardButton(label, callback_data=f"cat:{cat}:0")])
    btns.append([InlineKeyboardButton("🛠 最全免费工具 - Free Online Tools", url="https://toolmixr.com")])
    btns.append([InlineKeyboardButton("🤖 最新AI测评 - Latest AI Reviews", url="https://genaipick.com")])
    return InlineKeyboardMarkup(btns)

def search_resources(query, mx=8):
    q = query.lower()
    tms = [t.strip() for t in re.split(r'[\s,，、]+', q) if t.strip()]
    if not tms: return []
    return [item for item in SEARCH_INDEX if all(t in item["_search_text"] for t in tms)][:mx]

async def start(u, c):
    await u.message.reply_text(_(
        "👋 欢迎使用 **TG Search**！\n\n我是免费资源 + AI工具导航助手\n直接输入关键词就能搜索\n\n📌 **可用命令**\n/search <关键词> — 搜索\n/categories — 所有分类（可点击）\n/daily — 每日推荐\n/help — 帮助",
        "👋 Welcome to **TG Search**!\n\nFree Resources + AI Tools Navigator\nJust type keywords to search\n\n📌 **Commands**\n/search <keyword> — Search\n/categories — Browse (clickable)\n/daily — Daily pick\n/help — Help"
    ), parse_mode="Markdown", reply_markup=build_menu_kb())

async def help_cmd(u, c):
    await u.message.reply_text(_(
        "📖 **使用帮助**\n\n🔍 /search 关键词 — 搜索\n📂 /categories — 点击分类浏览\n⭐ /daily — 每日推荐\n📝 /submit 名称:简介:链接 — 投稿\n\n💡 或直接输入文字自动搜索",
        "📖 **Help**\n\n🔍 /search keyword — Search\n📂 /categories — Tap to browse\n⭐ /daily — Daily pick\n📝 /submit Name:Desc:URL — Submit\n\n💡 Or just type to search"
    ), parse_mode="Markdown")

async def categories(u, c):
    await u.message.reply_text(_(
        "📂 **资源分类**\n\n👇 点击分类查看资源",
        "📂 **Categories**\n\n👇 Tap a category to browse"
    ), parse_mode="Markdown", reply_markup=build_menu_kb())

async def search(u, c):
    text = u.message.text.strip()
    q = text.replace("/search", "", 1).strip() if text.startswith("/search") else text
    if not q or len(q) < 2:
        await u.message.reply_text(_("🔍 请输入关键词\n例如 /search 翻译 或直接发送「翻译」","🔍 Enter keywords\nE.g. /search translate")); return
    results = search_resources(q)
    if not results:
        await u.message.reply_text(_(f"😅 没找到「{q}」相关的资源\n试试其他关键词或用 /categories",f"😅 No results for \"{q}\"\nTry other keywords or /categories")); return
    grp = defaultdict(list)
    for r in results: grp[r["category"]].append(r)
    msg = _(f"🔍 **「{q}」结果（{len(results)} 条）**\n\n",f"🔍 **{q}** ({len(results)} results)\n\n")
    for cat, items in grp.items():
        for item in items: msg += f"  • [{item['name']}]({item['url']}) — {item['desc'][:50]}\n"; msg += "\n"
    await u.message.reply_text(msg, parse_mode="Markdown", disable_web_page_preview=True)

async def daily(u, c):
    cat = random.choice(CATEGORIES); item = random.choice(RESOURCES[cat])
    msg = _("⭐ **今日推荐 / Daily Pick**\n\n","⭐ **Daily Pick**\n\n")
    msg += f"{get_emoji(cat)} **{item['name']}**\n   {item['desc']}\n   🔗 {item['url']}\n   📂 {cat}"
    await u.message.reply_text(msg, parse_mode="Markdown")

async def submit(u, c):
    text = u.message.text.replace("/submit", "", 1).strip()
    if not text or ":" not in text:
        await u.message.reply_text(_("📝 **Format:**\n/submit 名称:简介:链接\n例: /submit Notion AI:AI笔记:https://notion.so","📝 Format:\n/submit Name:Desc:URL")); return
    parts = text.split(":", 2)
    if len(parts) < 3: await u.message.reply_text(_("格式不对","Invalid format")); return
    n, d, url = [p.strip() for p in parts]
    logger.info(f"投稿: {n}")
    await u.message.reply_text(_(f"✅ 收到「{n}」！审核后收录 🎉",f"✅ Thanks! \"{n}\" 🎉"))

async def text_handler(u, c):
    try:
        text = u.message.text.strip()
        if len(text) < 2: return
        if u.message.chat.type in ("group", "supergroup"):
            if BOT_USERNAME.lower() not in text.lower(): return
            text = re.sub(r'@\w+', '', text).strip()
        await search(u, c)
    except Exception as e: logger.error(f"txt: {e}")

async def button_handler(u, c):
    try:
        q = u.callback_query; await q.answer(); d = q.data
        if d == "back_cats":
            await q.edit_message_text(_("📂 **资源分类**\n\n👇 点击分类查看资源","📂 **Categories**\n\n👇 Tap a category to browse"),
                parse_mode="Markdown", reply_markup=build_menu_kb())
            return
        if d.startswith("cat:"):
            parts = d.split(":"); cat_name = parts[1]; page = int(parts[2]) if len(parts) > 2 else 0
            if cat_name not in RESOURCES: return
            items = RESOURCES[cat_name]; total = len(items)
            tp = (total + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE
            s = page * ITEMS_PER_PAGE; e = min(s + ITEMS_PER_PAGE, total)
            msg = f"{get_emoji(cat_name)} **{cat_name}** ({total}) — {CATEGORY_EN.get(cat_name, '')}\n\n"
            for i in range(s, e):
                item = items[i]
                msg += f"{i+1}. [{item['name']}]({item['url']})\n   {item['desc'][:60]}\n\n"
            nav_row = []
            if page > 0: nav_row.append(InlineKeyboardButton("◀️", callback_data=f"cat:{cat_name}:{page-1}"))
            nav_row.append(InlineKeyboardButton(f"{page+1}/{tp}", callback_data="noop"))
            if page < tp - 1: nav_row.append(InlineKeyboardButton("▶️", callback_data=f"cat:{cat_name}:{page+1}"))
            btns = [nav_row, [InlineKeyboardButton("📂 Back / 返回", callback_data="back_cats")]]
            await q.edit_message_text(msg, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(btns), disable_web_page_preview=True)
    except Exception as e: logger.error(f"btn: {e}")

async def error_handler(u, c): logger.error(f"Err: {c.error}")

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
    print("tgsearch started...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
