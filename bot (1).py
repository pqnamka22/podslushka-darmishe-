
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ContentType
from aiogram.utils import executor
from datetime import datetime

TOKEN = "8168424922:AAEi0QOsZ4iX9K0e7JiU1PiRqlIZIaXb4sc"
OWNER_ID = 8233512755

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

waiting_for_message = set()
chat_history = {}        # {user_id: [ {from, type, content} ]}
reply_sessions = {}     # {owner_id: user_id}


# ---------- KEYBOARDS ----------

def main_kb():
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("📩 Отправить сообщение", callback_data="send_message"))
    return kb


def owner_kb(user_id):
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("✍️ Ответить", callback_data=f"reply_{user_id}"),
        InlineKeyboardButton("📜 История", callback_data=f"history_{user_id}")
    )
    return kb


def cancel_kb():
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("❌ Отмена", callback_data="cancel_reply"))
    return kb


# ---------- START ----------

@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    chat_history.setdefault(message.from_user.id, [])
    await message.answer(
        "👋 Привет!\n\n"
        "Можешь отправить **любой контент**:\n"
        "текст, фото, видео, кружок, голосовое.\n\n"
        "Жми кнопку 👇",
        reply_markup=main_kb(),
        parse_mode="Markdown"
    )


# ---------- USER FLOW ----------

@dp.callback_query_handler(lambda c: c.data == "send_message")
async def send_message_cb(cb: types.CallbackQuery):
    waiting_for_message.add(cb.from_user.id)
    await cb.answer()
    await bot.send_message(cb.from_user.id, "📨 Отправляй сообщение")


@dp.message_handler(content_types=ContentType.ANY)
async def universal_handler(message: types.Message):
    user_id = message.from_user.id

    # ===== OWNER REPLY MODE =====
    if user_id == OWNER_ID and OWNER_ID in reply_sessions:
        to_user = reply_sessions.pop(OWNER_ID)
        await message.copy_to(to_user)

        chat_history.setdefault(to_user, []).append({
            "from": "owner",
            "type": message.content_type,
            "content": message.caption or message.text
        })

        await message.answer("✅ Ответ отправлен")
        return

    # ===== IGNORE RANDOM =====
    if user_id not in waiting_for_message:
        return

    waiting_for_message.discard(user_id)

    chat_history.setdefault(user_id, []).append({
        "from": "user",
        "type": message.content_type,
        "content": message.caption or message.text
    })

    await message.reply("✅ Сообщение отправлено!")

    username = f"@{message.from_user.username}" if message.from_user.username else message.from_user.full_name
    time_str = datetime.utcnow().strftime("%d.%m.%Y %H:%M UTC")

    await bot.send_message(
        OWNER_ID,
        f"📨 **Новое сообщение**\n"
        f"👤 {username}\n"
        f"🕒 {time_str}",
        reply_markup=owner_kb(user_id),
        parse_mode="Markdown"
    )

    await message.copy_to(OWNER_ID)


# ---------- OWNER CONTROLS ----------

@dp.callback_query_handler(lambda c: c.data.startswith("reply_"))
async def reply_cb(cb: types.CallbackQuery):
    reply_sessions[OWNER_ID] = int(cb.data.split("_")[1])
    await cb.answer()
    await bot.send_message(
        OWNER_ID,
        "✍️ Напишите ответ",
        reply_markup=cancel_kb()
    )


@dp.callback_query_handler(lambda c: c.data == "cancel_reply")
async def cancel_reply(cb: types.CallbackQuery):
    reply_sessions.pop(OWNER_ID, None)
    await cb.answer()
    await bot.send_message(OWNER_ID, "❌ Ответ отменён")


@dp.callback_query_handler(lambda c: c.data.startswith("history_"))
async def history_cb(cb: types.CallbackQuery):
    user_id = int(cb.data.split("_")[1])
    await cb.answer()

    history = chat_history.get(user_id, [])[-6:]
    if not history:
        await bot.send_message(OWNER_ID, "История пуста")
        return

    text = "📜 **Последние сообщения:**\n\n"
    for h in history:
        who = "👤" if h["from"] == "user" else "🤖"
        content = h["content"] or f"[{h['type']}]"
        text += f"{who} {content}\n"

    await bot.send_message(OWNER_ID, text, parse_mode="Markdown")


# ---------- RUN ----------

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)

   
