from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
import os
from datetime import datetime
import random
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CallbackQueryHandler, MessageHandler, filters, ContextTypes

list_is_open = True
students_list = {}

# قائمة الأدعية
duas = [
    "اللَّهُمَّ إِنِّي أَسْأَلُكَ العَفْوَ وَالعَافِيَةَ فِي الدُّنْيَا وَالآخِرَةِ",
    "اللَّهُمَّ آتِنَا في الدُّنْيَا حَسَنَةً وَفي الآخِرَةِ حَسَنَةً وَقِنَا عَذَابَ النَّارِ",
    "اللَّهُمَّ يَا مُقَلِّبَ القُلُوبِ ثَبِّتْ قَلْبِي عَلَى دِينِكَ",
    "رَبِّ أَعِنِّى وَلا تُعِنْ عَلَيَّ، وَانْصُرْنِي وَلا تَنْصُرْ عَلَيَّ",
    "اللَّهُمَّ إِنِّي أَعُوذُ بِكَ مِنْ زَوَالِ نِعْمَتِكَ، وَتَحَوُّلِ عَافِيَتِكَ، وَفُجَاءَةِ نِقْمَتِكَ"
]

def get_hijri_date():
    now = datetime.now()
    days_diff = (now - datetime(2026, 6, 16)).days  
    hijri_months = [
        ("محرم", 29), ("صفر", 30), ("ربيع الأول", 29), ("ربيع الآخر", 30),
        ("جمادى الأولى", 30), ("جمادى الآخرة", 29), ("رجب", 30), ("شعبان", 30),
        ("رمضان", 29), ("شوال", 30), ("ذو القعدة", 29), ("ذو الحجة", 30)
    ]
    h_year = 1448
    current_day_count = max(0, days_diff)
    m_index = 0
    while current_day_count >= hijri_months[m_index][1]:
        current_day_count -= hijri_months[m_index][1]
        m_index += 1
        if m_index >= 12:
            m_index = 0
            h_year += 1
    h_day = current_day_count + 1
    h_month_name = hijri_months[m_index][0]
    return f"{h_day} {h_month_name} {h_year} هـ"

def get_current_date():
    now = datetime.now()
    days_ar = {"Sunday": "الأحد", "Monday": "الإثنين", "Tuesday": "الثلاثاء", "Wednesday": "الأربعاء", "Thursday": "الخميس", "Friday": "الجمعة", "Saturday": "السبت"}
    months_ar = {1: "يناير", 2: "فبراير", 3: "مارس", 4: "أبريل", 5: "مايو", 6: "يونيو", 7: "يوليو", 8: "أغسطس", 9: "سبتمبر", 10: "أكتوبر", 11: "نوفمبر", 12: "ديسمبر"}
    
    day_name = days_ar.get(now.strftime("%A"), "")
    day_num = now.strftime("%d")
    month_name = months_ar.get(now.month, "")
    year_num = now.strftime("%Y")
    hijri_date = get_hijri_date()
    
    return f"{day_name} {day_num} {month_name} {year_num} مـ — {hijri_date}"

def get_formatted_text():
    status_text = "مفتوحة 🔓" if list_is_open else "مغلقة 🔒"
    selected_dua = random.choice(duas)
    decorations = ["🍃 ⃞ـ💎", "👑 ⃞ـ💎"]
    
    roles_text = ""
    for idx, (uid, data) in enumerate(students_list.items(), 1):
        deco = decorations[(idx - 1) % len(decorations)]
        profile_link = f"<a href='tg://user?id={uid}'>{data['name']}</a>"
        roles_text += f"{idx} {deco} {profile_link} — {data['riwaya']} {data['status']}\n"
    
    if not roles_text:
        roles_text = "لا توجد أدوار مسجلة حالياً.\n"

    return f"""👑 أكاديمية نور العلم للقراءة والإقراء والمتون العلمية 👑

📅 {get_current_date()}

<b>🌹 حلقة إجازة حفظ القرآن الكريم بالقراءات العشر 🌹</b>

حالة القائمة: {status_text}

❖──────────────────❖
<u>قائمة الأدواࢪ:</u> 

{roles_text}
❖──────────────────❖
🌹 {selected_dua} 🌹"""

def get_channel_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📝 أريد دور قراءة", callback_data="register_name")],
        [InlineKeyboardButton("❌ إزالة اسمي", callback_data="delete_name")],
        [InlineKeyboardButton("⚙️ لوحة إعدادات المشرف/ة", callback_data="admin_main")]
    ])

def get_admin_keyboard():
    toggle_text = "🔒 إغلاق القائمة" if list_is_open else "🔓 فتح القائمة"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(toggle_text, callback_data="toggle_list")],
        [InlineKeyboardButton("✅ تعليم من قرأ", callback_data="admin_mark_list")],
        [InlineKeyboardButton("🔄 بدء قائمة جديدة", callback_data="reset_new_list")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="back_to_main")]
    ])

def get_mark_student_keyboard():
    keyboard = []
    for uid, data in students_list.items():
        keyboard.append([InlineKeyboardButton(f"👤 {data['name']}", callback_data=f"mark_{uid}")])
    keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data="admin_main")])
    return InlineKeyboardMarkup(keyboard)

riwayat_dict = {
    "نافع": ["قالون", "ورش"],
    "ابن كثير": ["البزي", "قنبل"],
    "أبو عمرو": ["الدوري", "السوسي"],
    "ابن عامر": ["هشام", "ابن ذكوان"],
    "عاصم": ["شعبة", "حفص"],
    "حمزة": ["خلف", "خلّاد"],
    "الكسائي": ["أبي الحارث", "الدوري"],
    "أبو جعفر": ["إبن وردان", "إبن جماز"],
    "يعقوب": ["رويس", "روُح"],
    "خلف العاشر": ["إسحاق", "إدريس"]
}

def get_readers_keyboard():
    keyboard = []
    for reader in riwayat_dict.keys():
        keyboard.append([InlineKeyboardButton(f"📖 الإمام {reader}", callback_data=f"reg_reader_{reader}")])
    keyboard.append([InlineKeyboardButton("🔙 إلغاء", callback_data="back_to_main")])
    return InlineKeyboardMarkup(keyboard)

def get_riwayat_keyboard(reader_name):
    keyboard = []
    for riwaya in riwayat_dict.get(reader_name, []):
        keyboard.append([InlineKeyboardButton(f"🔹 رواية/طريق {riwaya}", callback_data=f"reg_riwaya_{riwaya}")])
    keyboard.append([InlineKeyboardButton("🔙 رجوع للقراء", callback_data="register_name")])
    return InlineKeyboardMarkup(keyboard)

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = get_formatted_text()
    reply_markup = get_channel_keyboard()
    
    target_message = update.message or update.channel_post
    
    if target_message:
        await target_message.reply_text(text, parse_mode="HTML", reply_markup=reply_markup)
    elif update.callback_query:
        try:
            await update.callback_query.message.edit_text(text, parse_mode="HTML", reply_markup=reply_markup)
        except:
            pass

async def is_user_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    user = update.callback_query.from_user
    chat = update.callback_query.message.chat
    if chat.type == "private":
        return True
    try:
        member = await context.bot.get_chat_member(chat.id, user.id)
        return member.status in ["creator", "administrator"]
    except:
        return False

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global list_is_open
    query = update.callback_query
    
    try:
        await query.answer()
    except:
        pass

    data = query.data
    user_id = query.from_user.id
    user_name = query.from_user.full_name

    admin_actions = ["admin_main", "toggle_list", "reset_new_list", "admin_mark_list"]
    if data in admin_actions or data.startswith("mark_"):
        if not await is_user_admin(update, context):
            try:
                await query.answer("هذا خاص بالمشرفين فقط ❌", show_alert=True)
            except:
                pass
            return

    if data == "admin_main":
        await query.message.edit_text("⚙️ لوحة تحكم المشرف/ة:", reply_markup=get_admin_keyboard())

    elif data == "admin_mark_list":
        if not students_list:
            await query.answer("القائمة فارغة!", show_alert=True)
        else:
            await query.message.edit_text("اختر الطالب لتعليمه بأنه قرأ:", reply_markup=get_mark_student_keyboard())

    elif data.startswith("mark_"):
        target_uid = int(data.split("_")[1])
        if target_uid in students_list:
            students_list[target_uid]['status'] = "✅"
            await show_main_menu(update, context)

    elif data == "register_name":
        if not list_is_open:
            await query.answer("عذراً انتهى وقت تسجيل الأدوار 🔒", show_alert=True)
            return
        if user_id in students_list:
            await query.answer("أنت مسجل في القائمة بالفعل ⚠️", show_alert=True)
            return
        await query.message.edit_text("اختر الإمام لتحديد روايتك:", reply_markup=get_readers_keyboard())

    elif data == "delete_name":
        if user_id in students_list:
            del students_list[user_id]
            await show_main_menu(update, context)
        else:
            await query.answer("اسمك غير مسجل في القائمة أصلاً!", show_alert=True)

    elif data.startswith("reg_reader_"):
        reader_name = data.split("_")[2]
        await query.message.edit_text(f"اختر رواية أو طريق عن الإمام {reader_name}:", reply_markup=get_riwayat_keyboard(reader_name))

    elif data.startswith("reg_riwaya_"):
        riwaya_name = data.split("_")[2]
        students_list[user_id] = {"name": user_name, "riwaya": riwaya_name, "status": "❓"}
        await show_main_menu(update, context)

    elif data == "toggle_list":
        list_is_open = not list_is_open
        if not list_is_open:
            await query.message.chat.send_message("🔒 **عذراً، تم إغلاق باب التسجيل في القائمة الآن.**", parse_mode="Markdown")
        else:
            await query.message.chat.send_message("🔓 **تم فتح باب التسجيل في القائمة، يمكنكم الآن حجز أدواركم.**", parse_mode="Markdown")
        await query.message.edit_text("⚙️ لوحة تحكم المشرف/ة:", reply_markup=get_admin_keyboard())

    elif data == "reset_new_list":
        students_list.clear()
        await query.message.edit_text("تم بدء قائمة جديدة ✅\n⚙️ لوحة تحكم المشرف/ة:", reply_markup=get_admin_keyboard())

    elif data == "back_to_main":
        await show_main_menu(update, context)

async def handle_text_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.channel_post
    if not msg or not msg.text:
        return
    text = msg.text.strip()
    
    # الاستجابة فقط لصيغ كلمة إجازة
    allowed_words = ["إجازة", "اجازه", "اجازة"]
    if text in allowed_words:
        await show_main_menu(update, context)

class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running successfully!")

def run_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), SimpleHandler)
    server.serve_forever()

def main():
    threading.Thread(target=run_server, daemon=True).start()

    app = ApplicationBuilder().token("8818665087:AAGPBN9ODdoBjwl4LtVcfWrHdQJQO8HrNrY").build()

    app.add_handler(MessageHandler((filters.TEXT & ~filters.COMMAND), handle_text_messages))
    app.add_handler(CallbackQueryHandler(button_handler))

    print("البوت يعمل الآن بنجاح...")
    app.run_polling()

if __name__ == "__main__":
    main()

