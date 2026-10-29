import os
import sqlite3
import logging
from datetime import datetime
from dotenv import load_dotenv

from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup
)
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters
)

load_dotenv()
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)
log = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_ID_RAW = os.getenv("ADMIN_ID", "").strip()
ADMIN_ID = int(ADMIN_ID_RAW) if ADMIN_ID_RAW.isdigit() else 0
CARD_NUMBER = os.getenv("CARD_NUMBER", "شماره کارت را مدیر در فایل .env تنظیم کند").strip()
CARDHOLDER = os.getenv("CARDHOLDER", "نام صاحب کارت را مدیر در فایل .env تنظیم کند").strip()
DB_PATH = os.getenv("DB_PATH", "orders.db")

CHANNELS = [
    ("کانال VPNIC", "https://t.me/VPNIC_NET", "@VPNIC_NET"),
    ("کانال دوم", "https://t.me/gghvchvh", "@gghvchvh"),
    ("کانال سوم", "https://t.me/meliiivpn", "@meliiivpn"),
    ("کانال چهارم", "https://t.me/fotbal_1388", "@fotbal_1388"),
]

PRODUCTS = {
    "gaming": {
        "name": "کانفیگ گیمینگ",
        "price": 12000,
        "minimum": 10,
        "unit": "گیگابایت",
        "description": "مناسب بازی آنلاین",
    },
    "web": {
        "name": "کانفیگ وب‌گردی",
        "price": 8000,
        "minimum": 10,
        "unit": "گیگابایت",
        "description": "مناسب وب‌گردی",
    },
    "panel": {
        "name": "پنل فروش کانفیگ VPN",
        "price": 13500,
        "minimum": 300,
        "unit": "گیگابایت",
        "description": "پنل فروش کانفیگ",
    },
    "wireguard": {
        "name": "پنل فروش WireGuard",
        "price": 15000,
        "minimum": 300,
        "unit": "گیگابایت",
        "description": "پنل فروش WireGuard",
    },
}


def db():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con


def init_db():
    with db() as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                username TEXT,
                product_key TEXT NOT NULL,
                product_name TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                total INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'awaiting_receipt',
                created_at TEXT NOT NULL,
                receipt_file_id TEXT,
                delivered_at TEXT
            )
        """)


def money(value):
    return f"{value:,}"


def joined_keyboard():
    rows = [[InlineKeyboardButton(f"عضویت: {name}", url=url)] for name, url, _ in CHANNELS]
    rows.append([InlineKeyboardButton("✅ بررسی عضویت", callback_data="check_membership")])
    return InlineKeyboardMarkup(rows)


def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎮 کانفیگ گیمینگ", callback_data="product:gaming")],
        [InlineKeyboardButton("🌐 کانفیگ وب‌گردی", callback_data="product:web")],
        [InlineKeyboardButton("🛒 پنل فروش کانفیگ VPN", callback_data="product:panel")],
        [InlineKeyboardButton("🛡 پنل فروش WireGuard", callback_data="product:wireguard")],
        [InlineKeyboardButton("📦 پیگیری سفارش", callback_data="my_orders")],
    ])


async def is_member(bot, user_id):
    for _, _, chat_id in CHANNELS:
        try:
            member = await bot.get_chat_member(chat_id=chat_id, user_id=user_id)
            if member.status in ("left", "kicked"):
                return False
        except Exception as exc:
            log.warning("Membership check failed for %s: %s", chat_id, exc)
            return False
    return True


async def show_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not await is_member(context.bot, user.id):
        text = (
            "سلام! به فروشگاه VPNIC خوش اومدی 👋\n\n"
            "برای استفاده از ربات، اول عضو هر ۴ کانال زیر شو؛ "
            "بعد روی «بررسی عضویت» بزن."
        )
        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=joined_keyboard())
        else:
            await update.effective_message.reply_text(text, reply_markup=joined_keyboard())
        return
    context.user_data.pop("awaiting_quantity", None)
    text = (
        "🟦 فروشگاه VPNIC\n\n"
        "یکی از محصولات زیر رو انتخاب کن.\n"
        "پرداخت با کارت‌به‌کارت انجام می‌شه و سفارش پس از بررسی مدیر تحویل داده می‌شه."
    )
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=main_menu())
    else:
        await update.effective_message.reply_text(text, reply_markup=main_menu())


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_start(update, context)


async def callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    user = update.effective_user

    if q.data == "check_membership":
        if await is_member(context.bot, user.id):
            await q.edit_message_text(
                "عضویت بررسی شد ✅\n\nبه فروشگاه VPNIC خوش اومدی!",
                reply_markup=main_menu()
            )
        else:
            await q.answer("هنوز عضویت هر ۴ کانال تأیید نشده؛ اگر عضو شدی دوباره امتحان کن.", show_alert=True)
        return

    if q.data.startswith("product:"):
        if not await is_member(context.bot, user.id):
            await q.edit_message_text(
                "برای ادامه، ابتدا عضو هر ۴ کانال شو.",
                reply_markup=joined_keyboard()
            )
            return
        key = q.data.split(":", 1)[1]
        product = PRODUCTS.get(key)
        if not product:
            await q.edit_message_text("محصول پیدا نشد.", reply_markup=main_menu())
            return
        context.user_data["awaiting_quantity"] = key
        await q.edit_message_text(
            f"🛍 {product['name']}\n"
            f"💵 قیمت هر گیگ: {money(product['price'])} تومان\n"
            f"📦 حداقل خرید: {product['minimum']} گیگ\n\n"
            f"تعداد گیگ موردنظرت رو به عدد بفرست:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("↩️ بازگشت به فروشگاه", callback_data="back_menu")]
            ])
        )
        return

    if q.data == "back_menu":
        context.user_data.pop("awaiting_quantity", None)
        await q.edit_message_text("فروشگاه VPNIC — محصول موردنظر رو انتخاب کن:", reply_markup=main_menu())
        return

    if q.data == "my_orders":
        with db() as con:
            orders = con.execute(
                "SELECT id, product_name, quantity, total, status, created_at "
                "FROM orders WHERE user_id=? ORDER BY id DESC LIMIT 10",
                (user.id,)
            ).fetchall()
        if not orders:
            await q.edit_message_text("هنوز سفارشی نداری.", reply_markup=main_menu())
            return
        status_names = {
            "awaiting_receipt": "منتظر رسید",
            "review": "در انتظار بررسی پرداخت",
            "paid": "پرداخت تأیید شده؛ منتظر تحویل",
            "delivered": "تحویل داده شده",
            "rejected": "رد شده",
        }
        lines = ["📦 آخرین سفارش‌های تو:"]
        for o in orders:
            lines.append(
                f"\n#{o['id']} — {o['product_name']}\n"
                f"{o['quantity']} گیگ | {money(o['total'])} تومان\n"
                f"وضعیت: {status_names.get(o['status'], o['status'])}"
            )
        await q.edit_message_text("\n".join(lines), reply_markup=main_menu())
        return

    if q.data.startswith("approve:") or q.data.startswith("reject:"):
        if user.id != ADMIN_ID:
            await q.answer("این دکمه فقط برای مدیر است.", show_alert=True)
            return
        action, order_id_text = q.data.split(":", 1)
        order_id = int(order_id_text)
        with db() as con:
            order = con.execute("SELECT * FROM orders WHERE id=?", (order_id,)).fetchone()
            if not order:
                await q.edit_message_text("سفارش پیدا نشد.")
                return
            if action == "reject":
                con.execute("UPDATE orders SET status='rejected' WHERE id=?", (order_id,))
                await context.bot.send_message(
                    order["user_id"],
                    f"❌ رسید سفارش #{order_id} تأیید نشد. برای راهنمایی با مدیر تماس بگیر."
                )
                await q.edit_message_text(f"رسید سفارش #{order_id} رد شد.")
                return
            con.execute("UPDATE orders SET status='paid' WHERE id=?", (order_id,))
        await context.bot.send_message(
            order["user_id"],
            f"✅ پرداخت سفارش #{order_id} توسط مدیر تأیید شد.\n"
            "سفارش در صف آماده‌سازی است؛ پس از تحویل، ربات بهت پیام می‌ده."
        )
        delivery_keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("📨 ارسال کانفیگ/اطلاعات پنل", callback_data=f"deliver:{order_id}")
        ]])
        await q.edit_message_text(
            f"✅ پرداخت سفارش #{order_id} تأیید شد.\n"
            "برای تحویل دستی، دکمه زیر رو بزن و سپس متن کانفیگ یا اطلاعات پنل رو ارسال کن.",
            reply_markup=delivery_keyboard
        )
        return

    if q.data.startswith("deliver:"):
        if user.id != ADMIN_ID:
            await q.answer("این دکمه فقط برای مدیر است.", show_alert=True)
            return
        order_id = int(q.data.split(":", 1)[1])
        with db() as con:
            order = con.execute("SELECT * FROM orders WHERE id=?", (order_id,)).fetchone()
        if not order or order["status"] != "paid":
            await q.answer("این سفارش آماده تحویل نیست.", show_alert=True)
            return
        context.user_data["awaiting_delivery_order"] = order_id
        await q.message.reply_text(
            f"متن کانفیگ یا اطلاعات پنل سفارش #{order_id} رو در همین چت بفرست.\n"
            "این متن مستقیماً برای خریدار ارسال می‌شه."
        )
        return


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = (update.effective_message.text or "").strip()

    # Admin delivery flow
    delivery_order_id = context.user_data.get("awaiting_delivery_order")
    if user.id == ADMIN_ID and delivery_order_id:
        with db() as con:
            order = con.execute("SELECT * FROM orders WHERE id=?", (delivery_order_id,)).fetchone()
            if not order or order["status"] != "paid":
                context.user_data.pop("awaiting_delivery_order", None)
                await update.effective_message.reply_text("سفارش آماده تحویل نیست یا پیدا نشد.")
                return
            await context.bot.send_message(
                chat_id=order["user_id"],
                text=f"📦 سفارش #{delivery_order_id} آماده تحویل است:\n\n{text}"
            )
            con.execute(
                "UPDATE orders SET status='delivered', delivered_at=? WHERE id=?",
                (datetime.utcnow().isoformat(timespec="seconds"), delivery_order_id)
            )
        context.user_data.pop("awaiting_delivery_order", None)
        await update.effective_message.reply_text(f"تحویل سفارش #{delivery_order_id} ثبت شد ✅")
        return

    product_key = context.user_data.get("awaiting_quantity")
    if not product_key:
        await update.effective_message.reply_text("برای شروع /start رو بزن.")
        return

    if not text.isdigit():
        await update.effective_message.reply_text("لطفاً فقط تعداد گیگ رو به عدد بفرست؛ مثلاً 10")
        return

    quantity = int(text)
    product = PRODUCTS[product_key]
    if quantity < product["minimum"]:
        await update.effective_message.reply_text(
            f"حداقل خرید این محصول {product['minimum']} گیگ است. دوباره تعداد رو بفرست:"
        )
        return
    if quantity > 100000:
        await update.effective_message.reply_text("این مقدار خیلی زیاده؛ برای خرید عمده با مدیر هماهنگ کن.")
        return

    total = quantity * product["price"]
    with db() as con:
        cur = con.execute(
            """INSERT INTO orders
            (user_id, username, product_key, product_name, quantity, total, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, 'awaiting_receipt', ?)""",
            (
                user.id, user.username, product_key, product["name"],
                quantity, total, datetime.utcnow().isoformat(timespec="seconds")
            )
        )
        order_id = cur.lastrowid

    context.user_data.pop("awaiting_quantity", None)
    await update.effective_message.reply_text(
        f"🧾 خلاصه سفارش #{order_id}\n\n"
        f"محصول: {product['name']}\n"
        f"مقدار: {quantity} گیگ\n"
        f"قیمت هر گیگ: {money(product['price'])} تومان\n"
        f"💰 مبلغ قابل پرداخت: {money(total)} تومان\n\n"
        f"💳 شماره کارت: {CARD_NUMBER}\n"
        f"👤 به نام: {CARDHOLDER}\n\n"
        "پس از کارت‌به‌کارت، عکس رسید رو همین‌جا بفرست.\n"
        "رسید توسط مدیر بررسی می‌شه. لطفاً تا تأیید مدیر صبر کن."
    )


async def handle_receipt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    with db() as con:
        order = con.execute(
            "SELECT * FROM orders WHERE user_id=? AND status='awaiting_receipt' ORDER BY id DESC LIMIT 1",
            (user.id,)
        ).fetchone()
        if not order:
            await update.effective_message.reply_text("سفارش منتظر رسیدی پیدا نشد. برای خرید /start رو بزن.")
            return
        file_id = update.effective_message.photo[-1].file_id
        con.execute("UPDATE orders SET status='review', receipt_file_id=? WHERE id=?", (file_id, order["id"]))

    await update.effective_message.reply_text(
        f"رسید سفارش #{order['id']} برای مدیر ارسال شد ✅\n"
        "تا بررسی و تأیید پرداخت منتظر بمون."
    )
    if not ADMIN_ID:
        await update.effective_message.reply_text("⚠️ شناسه مدیر در تنظیمات ربات ثبت نشده؛ مدیر باید ADMIN_ID را تنظیم کند.")
        return
    username = f"@{user.username}" if user.username else "ندارد"
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ تأیید پرداخت", callback_data=f"approve:{order['id']}"),
        InlineKeyboardButton("❌ رد رسید", callback_data=f"reject:{order['id']}")
    ]])
    caption = (
        f"🧾 رسید جدید — سفارش #{order['id']}\n"
        f"کاربر: {user.full_name}\n"
        f"آیدی: {user.id}\n"
        f"یوزرنیم: {username}\n"
        f"محصول: {order['product_name']}\n"
        f"مقدار: {order['quantity']} گیگ\n"
        f"مبلغ: {money(order['total'])} تومان"
    )
    await context.bot.send_photo(
        chat_id=ADMIN_ID, photo=file_id, caption=caption, reply_markup=keyboard
    )


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.pop("awaiting_quantity", None)
    context.user_data.pop("awaiting_delivery_order", None)
    await update.effective_message.reply_text("عملیات لغو شد. برای شروع /start رو بزن.")


def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN is missing. Copy .env.example to .env and set BOT_TOKEN.")
    if not ADMIN_ID:
        raise RuntimeError("ADMIN_ID is missing or invalid in .env.")
    init_db()
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("cancel", cancel))
    app.add_handler(CallbackQueryHandler(callbacks))
    app.add_handler(MessageHandler(filters.PHOTO & filters.ChatType.PRIVATE, handle_receipt))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE, handle_text))
    log.info("VPNIC bot started.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
