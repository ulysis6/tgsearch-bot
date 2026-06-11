#!/usr/bin/env python3
import json, logging, os, re, random
from collections import defaultdict
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, filters, ContextTypes)

TOKEN = os.environ.get("TG_TOKEN", "")
TG_PROXY = os.environ.get("TG_PROXY", "")
RESOURCES_FILE = "resources.json"
BOT_USERNAME = "tgsearch_nav_all_bot"
ITEMS_PER_PAGE = 8

with open(RESOURCES_FILE, "r", encoding="utf-8") as f:
    RESOURCES = json.load(f)

CATEGORIES = list(RESOURCES.keys())
CATEGORY_EMOJIS = {"电子书资源":"\U0001f4da","学习资源":"\U0001f393","设计素材":"\U0001f3a8","软件工具":"\U0001f4bb","AI工具":"\U0001f916","效率模板":"\U0001f4cb","搞钱/副业资源":"\U0001f4b0"}
CATEGORY_EN = {"电子书资源":"E-books","学习资源":"Learning","设计素材":"Design","软件工具":"Software","AI工具":"AI Tools","效率模板":"Templates","搞钱/副业资源":"Money"}

SEARCH_INDEX = []
for cat, items in RESOURCES.items():
    for item in items:
        SEARCH_INDEX.append({**item, "category": cat,
            "_search_text": f"{item['name']} {item['desc']} {' '.join(item['tags'])} {cat}".lower()})

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

def search_resources(query):
    q = query.lower()
    terms = [t.strip() for t in re.split(r'[\s,，、]+', q) if t.strip()]
    if not terms: return []
    return [item for item in SEARCH_INDEX if all(t in item["_search_text"] for t in terms)]

def get_emoji(cat): return CATEGORY_EMOJIS.get(cat, "\U0001f4c1")

def cats_kb():
    buttons = []
    row = []
    for i, cat in enumerate(CATEGORIES):
        row.append(InlineKeyboardButton(f"{get_emoji(cat)} {cat}", callback_data=f"cat:{cat}:0"))
        if len(row) == 2: buttons.append(row); row = []
    if row: buttons.append(row)
    buttons.append([InlineKeyboardButton("\U0001f50d Search", switch_inline_query_current_chat=""), InlineKeyboardButton("\u2b50 Daily", callback_data="daily")])
    return InlineKeyboardMarkup(buttons)

def item_text(item, idx):
    emoji = get_emoji(item["category"])
    tags = "/".join(item["tags"][:4])
    return f"{idx}. {emoji} [{item['name']}]({item['url']})\n   {item['desc']}\n   \U0001f3f7\ufe0f {tags}\n"

def page_items(items, page):
    s = page * ITEMS_PER_PAGE
    e = min(s + ITEMS_PER_PAGE, len(items))
    return "".join(item_text(items[i], i+1) for i in range(s, e))

def page_kb(action, param, page, total, back="cats"):
    tp = (total + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE
    row = []
    if page > 0: row.append(InlineKeyboardButton("\u25c0\ufe0f", callback_data=f"{action}:{param}:{page-1}"))
    row.append(InlineKeyboardButton(f"{page+1}/{tp}", callback_data="noop"))
    if page < tp - 1: row.append(InlineKeyboardButton("\u25b6\ufe0f", callback_data=f"{action}:{param}:{page+1}"))
    return InlineKeyboardMarkup([row, [InlineKeyboardButton("\U0001f4c2 Categories", callback_data=back)]])

async def send_page(msg_obj, action, param, items, page):
    if action == "cat":
        en = CATEGORY_EN.get(param, param)
        data = f"{get_emoji(param)} **{param}** ({len(items)}) - Page {page+1}\n\U0001f4ac **{en}**\n\n" + page_items(items, page)
    else:
        data = f"\U0001f50d **{param}** - {len(items)} results\n\n" + page_items(items, page)
    await msg_obj.edit_message_text(data, parse_mode="Markdown", reply_markup=page_kb(action, param, page, len(items)), disable_web_page_preview=True)

async def start(update, context):
    await update.message.reply_text(
        "\U0001f44b **TG Search \u5bfc\u822a\u52a9\u624b**\n\U0001f4ac **TG Search Navigation Bot**\n\n\u5e2e\u6211\u641c\u7d22 **\u514d\u8d39\u8d44\u6e90 + AI\u5de5\u5177**\n\U0001f4ac Search **Free Resources + AI Tools**\n\n\U0001f447 \u9009\u62e9\u5206\u7c7b / Select a category:",
        parse_mode="Markdown", reply_markup=cats_kb())

async def categories_cmd(update, context):
    await update.message.reply_text("\U0001f4c2 **Categories / \u5206\u7c7b**\n\n\U0001f447 \u70b9\u51fb\u67e5\u770b / Click to browse:", parse_mode="Markdown", reply_markup=cats_kb())

async def search_cmd(update, context):
    text = update.message.text.strip()
    query = text.replace("/search", "", 1).strip() if text.startswith("/search") else text
    if not query or len(query) < 2:
        await update.message.reply_text("\U0001f50d \u8f93\u5165\u5173\u952e\u8bcd / Enter keywords", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("\U0001f4c2 Categories", callback_data="cats")]])); return
    results = search_resources(query)
    if not results:
        await update.message.reply_text(f"\U0001f605 No results: {query}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("\U0001f4c2 Categories", callback_data="cats")]])); return
    await update.message.reply_text(f"\U0001f50d **{query}** - {len(results)} results\n\n" + page_items(results, 0), parse_mode="Markdown", reply_markup=page_kb("srch", query, 0, len(results)), disable_web_page_preview=True)

async def daily(update, context):
    cat = random.choice(CATEGORIES)
    item = random.choice(RESOURCES[cat])
    await update.message.reply_text("\u2b50 **Daily Pick / \u4eca\u65e5\u63a8\u8350**\n\n" + item_text(item, 1), parse_mode="Markdown", disable_web_page_preview=True, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("\U0001f500 Another", callback_data="daily2"), InlineKeyboardButton("\U0001f4c2 Categories", callback_data="cats")]]))

async def submit_cmd(update, context):
    text = update.message.text.replace("/submit", "", 1).strip()
    if not text or ":" not in text:
        await update.message.reply_text("\U0001f4dd **Format:**\n/submit \u540d\u79f0:\u7b80\u4ecb:\u94fe\u63a5\n/\u4f8b: /submit Notion AI:AI\u7b46\u8bb0:https://notion.so"); return
    parts = text.split(":", 2)
    if len(parts) < 3: await update.message.reply_text("Invalid format"); return
    name, desc, url = [p.strip() for p in parts]
    logger.info(f"\u6295\u7a3f: {name}")
    await update.message.reply_text(f"\u2705 \u6536\u5230\u300c{name}\u300d\uff01\u5ba1\u6838\u540e\u6536\u5f55 \U0001f389\n\U0001f4ac Thanks!")

async def help_cmd(update, context):
    await update.message.reply_text("\U0001f4d6 **Help**\n\n\U0001f50d /search \u5173\u952e\u8bcd\n\U0001f4c2 /categories\n\u2b50 /daily\n\U0001f4dd /submit \u540d\u79f0:\u7b80\u4ecb:\u94fe\u63a5\n\n\U0001f4a1 All buttons clickable!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("\U0001f4c2 Start", callback_data="cats")]]))

async def text_handler(update, context):
    text = update.message.text.strip()
    if len(text) < 2: return
    if update.message.chat.type in ("group", "supergroup"):
        if BOT_USERNAME.lower() not in text.lower(): return
        text = re.sub(r'@\w+', '', text).strip()
    await search_cmd(update, context)

async def button_handler(update, context):
    q = update.callback_query
    await q.answer()
    d = q.data
    if d == "noop": return
    if d == "cats":
        await q.edit_message_text("\U0001f4c2 **Categories / \u5206\u7c7b**\n\n\U0001f447 \u70b9\u51fb\u67e5\u770b:", parse_mode="Markdown", reply_markup=cats_kb()); return
    if d in ("daily","daily2"):
        cat = random.choice(CATEGORIES); item = random.choice(RESOURCES[cat])
        await q.edit_message_text("\u2b50 **Daily Pick / \u4eca\u65e5\u63a8\u8350**\n\n" + item_text(item, 1), parse_mode="Markdown", disable_web_page_preview=True, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("\U0001f500 Another", callback_data="daily2"), InlineKeyboardButton("\U0001f4c2 Categories", callback_data="cats")]])); return
    if d.startswith("cat:"):
        parts = d.split(":", 2); items = RESOURCES.get(parts[1], [])
        if items: await send_page(q, "cat", parts[1], items, int(parts[2])); return
    if d.startswith("srch:"):
        parts = d.split(":", 2); results = search_resources(parts[1])
        if results: await send_page(q, "srch", parts[1], results, int(parts[2])); return

async def error_handler(update, context):
    logger.error(f"Error: {context.error}")

def main():
    builder = Application.builder().token(TOKEN)
    if TG_PROXY: builder.proxy_url(TG_PROXY)
    app = builder.build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("categories", categories_cmd))
    app.add_handler(CommandHandler("search", search_cmd))
    app.add_handler(CommandHandler("daily", daily))
    app.add_handler(CommandHandler("submit", submit_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_error_handler(error_handler)
    print("tgsearch v2 started...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
