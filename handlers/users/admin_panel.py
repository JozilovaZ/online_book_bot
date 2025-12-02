from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from aiogram.dispatcher.filters.state import State, StatesGroup
import logging

from data.config import ADMINS
from loader import dp, user_db
from keyboards.default.default_keyboard import menu_ichki_admin, menu_admin

# =================== STATE'LAR ===================
class AdminStates(StatesGroup):
    AddAdmin = State()
    RemoveAdmin = State()

# =================== YORDAMCHI FUNKSIYALAR ===================
async def get_user_role(telegram_id: int):
    """Foydalanuvchining rolini tekshiradi: 'super', 'admin', None"""
    if telegram_id in ADMINS:
        logging.info(f"User {telegram_id} is Super Admin")
        return "super"
    user = user_db.select_user(telegram_id=telegram_id)
    if not user:
        logging.info(f"User {telegram_id} not found in DB")
        return None
    user_id = user[0]
    if user_db.check_if_admin(user_id=user_id):
        logging.info(f"User {telegram_id} is Admin")
        return "admin"
    return None

# =================== ORTGA QAYTISH ===================
@dp.message_handler(Text("🔙 Ortga qaytish"))
async def back_handler(message: types.Message):
    telegram_id = message.from_user.id
    role = await get_user_role(telegram_id)
    if role in ["super", "admin"]:
        await message.answer(
            "🏠 <b>Bosh sahifa</b>\n\nKerakli bo'limni tanlang:",
            reply_markup=menu_admin
        )
    else:
        await message.reply("🚫 Sizda bu bo'limga kirish huquqi yo'q.")

# =================== ADMIN PANEL ===================
@dp.message_handler(commands="panel")
async def control_panel(message: types.Message):
    telegram_id = message.from_user.id
    role = await get_user_role(telegram_id)
    if role in ["super", "admin"]:
        admin_name = message.from_user.first_name
        role_text = "⭐️ Super Administrator" if role == "super" else "🔰 Administrator"
        await message.answer(
            f"🎛 <b>Boshqaruv paneli</b>\n\n"
            f"Salom, <b>{admin_name}</b>! 👋\n"
            f"Tizim boshqaruviga xush kelibsiz.\n\n"
            f"💼 Sizning huquqlaringiz: {role_text}\n\n"
            f"Kerakli bo'limni tanlang:",
            reply_markup=menu_admin
        )
    else:
        await message.reply(
            "🚫 <b>Kirish rad etildi!</b>\n\nSizda bu bo'limga kirish huquqi yo'q."
        )

# =================== ADMINLAR BOSHQARUVI ===================
@dp.message_handler(Text(equals="👥 Adminlar boshqaruvi"))
async def admin_control_menu(message: types.Message):
    telegram_id = message.from_user.id
    role = await get_user_role(telegram_id)
    if role != "super":
        await message.reply(
            "⚠️ <b>Ruxsat berilmadi</b>\nBu bo'lim faqat Super Adminlar uchun."
        )
        return

    admins = user_db.get_all_admins()
    admin_count = len(admins) + len(ADMINS)
    await message.answer(
        f"🛡 <b>Adminlar boshqaruvi</b>\n\n👤 Hozirgi adminlar: <b>{admin_count}</b> ta\n\n"
        "Bu bo'limda siz:\n• Yangi admin tayinlashingiz\n• Adminlarni o'chirishingiz\n• Barcha adminlarni ko'rishingiz mumkin\n\n"
        "Kerakli amalni tanlang:",
        reply_markup=menu_ichki_admin
    )

# =================== ADMIN QO'SHISH ===================
@dp.message_handler(Text(equals="➕ Admin qo'shish"))
async def add_admin(message: types.Message):
    telegram_id = message.from_user.id
    role = await get_user_role(telegram_id)
    if role != "super":
        await message.reply("⚠️ Faqat Super Adminlar yangi admin tayinlay oladi.")
        return

    await message.answer(
        "➕ <b>Yangi admin tayinlash</b>\n"
        "Telegram ID raqamini yuboring.\n"
        "💡 <i>ID ni qanday topish mumkin: Shaxsdan @userinfobot ga /start yuborishni so'rang</i>"
    )
    await AdminStates.AddAdmin.set()

@dp.message_handler(state=AdminStates.AddAdmin)
async def process_admin_add(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("❗️ Telegram ID faqat raqamlardan iborat bo'lishi kerak. Qaytadan kiriting:")
        return

    admin_telegram_id = int(message.text)
    user = user_db.select_user(telegram_id=admin_telegram_id)
    if not user:
        await message.answer("🔍 Foydalanuvchi topilmadi. Botga /start yuborishini so'rang.")
        await state.finish()
        return

    user_id, telegram_id, username = user[0], user[1], user[2]
    if user_db.check_if_admin(user_id=user_id):
        await message.answer(f"ℹ️ @{username} allaqachon admin. Boshqa ID kiriting yoki /panel orqali chiqish.")
        return  # state tugamaydi, foydalanuvchi yana ID kirita oladi

    user_db.add_admin(user_id=user_id, name=username)
    await message.answer(f"✅ @{username} admin tayinlandi.\n🆔 {telegram_id}")
    await state.finish()

# =================== ADMIN O'CHIRISH ===================
@dp.message_handler(Text(equals="❌ Adminni o'chirish"))
async def remove_admin(message: types.Message):
    telegram_id = message.from_user.id
    role = await get_user_role(telegram_id)
    if role != "super":
        await message.reply("⚠️ Faqat Super Adminlar adminlarni o'chirishi mumkin.")
        return

    await message.answer("🗑 Telegram ID raqamini yuboring. Super Adminlarni o'chirib bo'lmaydi.")
    await AdminStates.RemoveAdmin.set()

@dp.message_handler(state=AdminStates.RemoveAdmin)
async def process_admin_remove(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("❗️ Telegram ID faqat raqamlardan iborat bo'lishi kerak. Qaytadan kiriting:")
        return

    admin_telegram_id = int(message.text)
    user = user_db.select_user(telegram_id=admin_telegram_id)
    if not user:
        await message.answer("🔍 Foydalanuvchi topilmadi. ID tekshiring.")
        await state.finish()
        return

    user_id, telegram_id, username = user[0], user[1], user[2]
    if not user_db.check_if_admin(user_id=user_id):
        await message.answer(f"ℹ️ @{username} admin emas.")
        await state.finish()
        return

    if admin_telegram_id in ADMINS:
        await message.answer(f"🛡 @{username} Super Admin hisoblanadi. O'chirib bo'lmaydi.")
        await state.finish()
        return

    user_db.remove_admin(user_id=user_id)
    await message.answer(f"✅ @{username} endi admin emas.")
    await state.finish()

# =================== ADMINLAR RO'YXATI ===================
@dp.message_handler(Text(equals="👥 Barcha adminlar"))
async def list_all_admins(message: types.Message):
    telegram_id = message.from_user.id
    role = await get_user_role(telegram_id)
    if role not in ["super", "admin"]:
        await message.reply("🚫 Sizda bu ma'lumotni ko'rish huquqi yo'q.")
        return

    admins = user_db.get_all_admins()
    admin_list = []

    for admin in admins:
        is_super = admin['telegram_id'] in ADMINS
        badge = "⭐️" if is_super else "🔰"
        role_name = "Super Admin" if is_super else "Admin"
        admin_list.append(f"{badge} <b>{admin['name']}</b>\n    🆔 {admin['telegram_id']}\n    💼 {role_name}")

    for admin_id in ADMINS:
        if not any(a['telegram_id'] == admin_id for a in admins):
            admin_list.append(f"⭐️ <b>Super Admin</b>\n    🆔 {admin_id}\n    💼 Super Admin")

    if admin_list:
        header = "👥 <b>ADMINLAR RO'YXATI</b>\n\n" + "━━━━━━━━━━━━━━━━━━━\n\n"
        footer = "\n\n━━━━━━━━━━━━━━━━━━━\n📌 Eslatma: ⭐️ - Super Admin, 🔰 - Admin"
        await message.answer(header + "\n\n".join(admin_list) + footer)
    else:
        await message.answer("📋 Hozircha tizimda adminlar yo'q. Super Adminlar config faylida belgilanadi.")
