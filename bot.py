from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
import os
import random
import threading
import psycopg2
from psycopg2.extras import RealDictCursor
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ----------------- إعدادات قاعدة البيانات (PostgreSQL) -----------------
DATABASE_URL = os.environ.get("DATABASE_URL")

def get_db_connection():
    if not DATABASE_URL:
        raise ValueError("خطأ: متغير البيئة DATABASE_URL غير معرف أو مفقود في إعدادات المنصة!")
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS channel_settings (
            chat_id BIGINT PRIMARY KEY,
            list_is_open BOOLEAN DEFAULT TRUE
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS students (
            chat_id BIGINT,
            user_id BIGINT,
            name TEXT,
            riwaya TEXT,
            status TEXT,
            PRIMARY KEY (chat_id, user_id)
        )
    """)
    conn.commit()
    cursor.close()
    conn.close()

if DATABASE_URL:
    try:
        init_db()
    except Exception as e:
        print(f"Database Initialization Error: {e}")

def get_list_status(chat_id: int) -> bool:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT list_is_open FROM channel_settings WHERE chat_id = %s", (chat_id,))
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    if row is None:
        return True
    return row["list_is_open"]

def set_list_status(chat_id: int, is_open: bool):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO channel_settings (chat_id, list_is_open) VALUES (%s, %s)
        ON CONFLICT (chat_id) DO UPDATE SET list_is_open = EXCLUDED.list_is_open
    """, (chat_id, is_open))
    conn.commit()
    cursor.close()
    conn.close()

def get_students_list(chat_id: int) -> dict:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, name, riwaya, status FROM students WHERE chat_id = %s", (chat_id,))
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    
    students = {}
    for row in rows:
        students[row["user_id"]] = {
            "name": row["name"],
            "riwaya": row["riwaya"],
            "status": row["status"]
        }
    return students

def add_student(chat_id: int, user_id: int, name: str, riwaya: str, status: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO students (chat_id, user_id, name, riwaya, status) VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (chat_id, user_id) DO UPDATE SET name = EXCLUDED.name, riwaya = EXCLUDED.riwaya, status = EXCLUDED.status
    """, (chat_id, user_id, name, riwaya, status))
    conn.commit()
    cursor.close()
    conn.close()

def remove_student(chat_id: int, user_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM students WHERE chat_id = %s AND user_id = %s", (chat_id, user_id))
    conn.commit()
    cursor.close()
    conn.close()

def update_student_status(chat_id: int, user_id: int, status: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE students SET status = %s WHERE chat_id = %s AND user_id = %s", (status, chat_id, user_id))
    conn.commit()
    cursor.close()
    conn.close()

def clear_students(chat_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM students WHERE chat_id = %s", (chat_id,))
    conn.commit()
    cursor.close()
    conn.close()

# ----------------- النصوص والأدعية -----------------
duas = [
    "⊰💎⊱ رَبِّ أَعِنِّى وَلا تُعِنْ عَلَيَّ، وَانْصُرْنِي وَلا تَنْصُرْ عَلَيَّ ⊰💎⊱",
    "⊰🌺⊱ اللَّهُمَّ إِنِّي أَسْأَلُكَ العَفْوَ وَالعَافِيَةَ فِي الدُّنْيَا وَالآخِرَةِ ⊰🌺⊱",
    "⊰💎⊱ اللَّهُمَّ يَا مُقَلِّبَ القُلُوبِ ثَبِّتْ قَلْبِي عَلَى دِينِكَ ⊰💎⊱",
    "⊰🤲⊱ اللَّهُمَّ اجْعَلِ القُرْآنَ رَبِيعَ قُلُوبِنَا، وَنُورَ صُدُورِنَا ⊰🤲⊱",
]

motivations = [
    "«أهل القرآن هم أهل الله وخاصته» — هنيئاً لمن اختاره الله ليحفظ كلامه في صدره.",
    "قال ابن مسعود رضي الله عنه: «ينبغي لحامل القرآن أن يُعرف بليله إذا الناس نهار، وبنومه إذا الناس سهار».",
    "قال الإمام الشاطبي رحمه الله: «وفي الصدر قرآنٌ يورثُ صاحبه عِزّاً ومجدًا لا يُبارى».",
    "حفظ القرآن في الصدر يورث خشية الله، ورفعة في الدارين، ونوراً يقذفه الله في قلب صاحبه.",
    "القرآن كنزٌ لا يفنى، وكلما بذلتَ له وقتك وعزيمتك، أعطاك من بركاته وأسراره.",
]

def get_hijri_date():
    now = datetime.now()
    days_diff = (now - datetime(2026, 6, 16)).days
    hijri_months = [
        ("محرم", 29), ("صفر", 30), ("ربيع الأول", 29), ("ربيع الآخر", 30),
        ("جمادى الأولى", 30), ("جمادى الآخرة", 29), ("رجب", 30), ("شعبان", 30),
        ("رمضان", 29), ("شوال", 30), ("ذو القعدة", 30), ("ذو الحجة", 29),
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
    days_ar = {
        "Sunday": "الأحد", "Monday": "الإثنين", "Tuesday": "الثلاثاء",
        "Wednesday": "الأربعاء", "Thursday": "الخميس", "Friday": "الجمعة", "Saturday": "السبت"
    }
    months_ar = {
        1: "يناير", 2: "فبراير", 3: "مارس", 4: "أبريل", 5: "مايو", 6: "يونيو",
        7: "يوليو", 8: "أغسطس", 9: "سبتمبر", 10: "أكتوبر", 11: "نوفمبر", 12: "ديسمبر"
    }
    day_name = days_ar.get(now.strftime("%A"), "")
    day_num = now.strftime("%d")
    month_name = months_ar.get(now.month, "")
    year_num = now.strftime("%Y")
    hijri_date = get_hijri_date()
    return f"• {day_name} {day_num} {month_name} {year_num} مـ — {hijri_date}"

def get_formatted_text(chat_id: int):
    list_is_open = get_list_status(chat_id)
    students_list = get_students_list(chat_id)
    
    status_text = "مفتوحة 🔓 🟢" if list_is_open else "مغلقة 🔒 🔴"
    selected_dua = random.choice(duas)
    selected_motivation = random.choice(motivations)

    slot_icons = ["👑", "🕊", "🕋", "🌺"]
    roles_text = ""
    for idx, (uid, data) in enumerate(students_list.items(), 1):
        icon = slot_icons[(idx - 1) % len(slot_icons)]
        profile_link = f"<a href='tg://user?id={uid}'>{data['name']}</a>"
        roles_text += f"{idx} {icon} ⃞ـ💎 {profile_link} — {data['riwaya']} {data['status']}\n"

    if not roles_text:
        roles_text = "لا توجد أدوار مسجلة حتى الآن، بادر بحجز دورك.\n"

    return f"""📚👑   <b>أكاديمية نور العلم للقراءة والإقراء والمتون العلمية</b>    👑📚
<u>{get_current_date()}</u>

🌺✨⌯⌲ {selected_motivation} ⌯⌲✨🌺

•🌺🕊 <b>حلقة الإجازة في حفظ القرآن الكريم بالقراءات العشر</b> 🌺🕊

• <b>حالة القائمة:</b> {status_text}
​༄ؘ ۪۪۫۫ ▹◃ ༄ؘ ۪۪۫۫━━━━━━━━━━━━༄ؘ ۪۪۫۫ ▹◃ ༄ؘ ۪۪۫۫
✨📝 <b>قائمة الأدوار:</b> 📝✨

{roles_text}
​༄ؘ ۪۪۫۫ ▹◃ ༄ؘ ۪۪۫۫━━━━━━━━━━━━༄ؘ ۪۪۫۫ ▹◃ ༄ؘ ۪۪۫۫
{selected_dua}"""

# ----------------- لوحات المفاتيح -----------------
def get_channel_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💎 📝 أريد دور قراءة", callback_data="register_name")],
        [InlineKeyboardButton("❌ إزالة اسمي من القائمة", callback_data="delete_name")],
        [InlineKeyboardButton("⚙️ لوحة إعدادات المشرفين", callback_data="admin_main")],
    ])

def get_admin_keyboard(chat_id: int):
    list_is_open = get_list_status(chat_id)
    toggle_text = "🔒 إغلاق القائمة مؤقتاً" if list_is_open else "🔓 فتح القائمة للتسجيل"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(toggle_text, callback_data="toggle_list")],
        [InlineKeyboardButton("✅ تعليم من أتم القراءة", callback_data="admin_mark_list")],
        [InlineKeyboardButton("🔄 تدوير وبدء قائمة جديدة", callback_data="reset_new_list")],
        [InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data="back_to_main")],
    ])

def get_mark_student_keyboard(chat_id: int):
    students_list = get_students_list(chat_id)
    keyboard = []
    for uid, data in students_list.items():
        keyboard.append([InlineKeyboardButton(f"👤 {data['name']}", callback_data=f"mark_{uid}")])
    keyboard.append([InlineKeyboardButton("🔙 رجوع لوحة المشرفين", callback_data="admin_main")])
    return InlineKeyboardMarkup(keyboard)

riwayat_dict = {
    "نافع": ["قالون", "ورش"],
    "ابن كثير": ["ابن كثير"],
    "أبو عمرو": ["الدوري", "السوسي"],
    "ابن عامر": ["هشام", "ابن ذكوان"],
    "عاصم": ["شعبة", "حفص"],
    "حمزة": ["خلف", "خلّاد"],
    "الكسائي": ["أبي الحارث", "الدوري"],
    "أبو جعفر": ["إبن وردان", "إبن جماز"],
    "يعقوب": ["رويس", "روُح"],
    "خلف العاشر": ["إسحاق", "إدريس"],
}

def get_readers_keyboard():
    keyboard = []
    for reader in riwayat_dict.keys():
        keyboard.append([InlineKeyboardButton(f"📖 الإمام {reader}", callback_data=f"reg_reader_{reader}")])
    keyboard.append([InlineKeyboardButton("🔙 إلغاء والرجوع", callback_data="back_to_main")])
    return InlineKeyboardMarkup(keyboard)

def get_riwayat_keyboard(reader_name):
    keyboard = []
    for riwaya in riwayat_dict.get(reader_name, []):
        keyboard.append([InlineKeyboardButton(f"🔹 رواية/طريق {riwaya}", callback_data=f"reg_riwaya_{riwaya}")])
    keyboard.append([InlineKeyboardButton("🔙 رجوع لاختيار القراء", callback_data="register_name")])
    return InlineKeyboardMarkup(keyboard)

# ----------------- المعالجات ودوال العرض -----------------
async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query and query.message:
        chat_id = query.message.chat.id
    elif update.message:
        chat_id = update.message.chat.id
    elif update.channel_post:
        chat_id = update.channel_post.chat.id
    else:
        return

    text = get_formatted_text(chat_id)
    reply_markup = get_channel_keyboard()

    if query:
        try:
            await query.message.edit_text(text, parse_mode="HTML", reply_markup=reply_markup)
        except Exception:
            pass
    else:
        target_message = update.message or update.channel_post
        if target_message:
            await target_message.reply_text(text, parse_mode="HTML", reply_markup=reply_markup)

async def is_user_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    query = update.callback_query
    if not query or not query.from_user or not query.message:
        return False
    chat = query.message.chat
    if chat.type == "private":
        return True
    try:
        member = await context.bot.get_chat_member(chat.id, query.from_user.id)
        return member.status in ["creator", "administrator"]
    except Exception:
        return False

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query or not query.message:
        return

    chat_id = query.message.chat.id
    try:
        await query.answer()
    except Exception:
        pass

    data = query.data
    user_id = query.from_user.id
    user_name = query.from_user.full_name

    admin_actions = ["admin_main", "toggle_list", "reset_new_list", "admin_mark_list"]
    if data in admin_actions or data.startswith("mark_"):
        if not await is_user_admin(update, context):
            try:
                await query.answer("عذرًا، هذا الأمر يخص المشرفين فقط ❌", show_alert=True)
            except Exception:
                pass
            return

    try:
        if data == "admin_main":
            await query.message.edit_text("⚙️ لوحة تحكم المشرفين:", reply_markup=get_admin_keyboard(chat_id))

        elif data == "admin_mark_list":
            students_list = get_students_list(chat_id)
            if not students_list:
                await query.answer("القائمة فارغة تماماً!", show_alert=True)
            else:
                await query.message.edit_text("اختر الطالب لتعليم إتمامه القراءة:", reply_markup=get_mark_student_keyboard(chat_id))

        elif data.startswith("mark_"):
            target_uid = int(data.split("_")[1])
            students_list = get_students_list(chat_id)
            if target_uid in students_list:
                update_student_status(chat_id, target_uid, "✅")
                await show_main_menu(update, context)

        elif data == "register_name":
            list_is_open = get_list_status(chat_id)
            if not list_is_open:
                await query.answer("عذراً، باب التسجيل مغلق مؤقتاً 🔒", show_alert=True)
                return
            students_list = get_students_list(chat_id)
            if user_id in students_list:
                await query.answer("أنت مسجل بالفعل في هذه القائمة ⚠️", show_alert=True)
                return
            await query.message.edit_text("اختر الإمام الكريم لتحديد روايتك:", reply_markup=get_readers_keyboard())

        elif data == "delete_name":
            students_list = get_students_list(chat_id)
            if user_id in students_list:
                remove_student(chat_id, user_id)
                await show_main_menu(update, context)
            else:
                await query.answer("عذراً، اسمك غير مسجل في القائمة أصلاً!", show_alert=True)

        elif data.startswith("reg_reader_"):
            reader_name = data.split("_")[2]
            if reader_name == "ابن كثير":
                add_student(chat_id, user_id, user_name, "ابن كثير", "❓")
                await show_main_menu(update, context)
            else:
                await query.message.edit_text(f"اختر الرواية أو الطريق عن الإمام {reader_name}:", reply_markup=get_riwayat_keyboard(reader_name))

        elif data.startswith("reg_riwaya_"):
            riwaya_name = data.split("_")[2]
            add_student(chat_id, user_id, user_name, riwaya_name, "❓")
            await show_main_menu(update, context)

        elif data == "toggle_list":
            current_status = get_list_status(chat_id)
            new_status = not current_status
            set_list_status(chat_id, new_status)
            
            status_msg = "🔒 **عذراً، تم إغلاق باب التسجيل في القائمة الآن.**" if not new_status else "🔓 **تم فتح باب التسجيل في القائمة، يمكنكم الآن حجز أدواركم.**"
            try:
                await query.message.chat.send_message(status_msg, parse_mode="Markdown")
            except Exception:
                pass
            await query.message.edit_text("⚙️ لوحة تحكم المشرفين:", reply_markup=get_admin_keyboard(chat_id))

        elif data == "reset_new_list":
            clear_students(chat_id)
            await query.message.edit_text("تم بدء قائمة جديدة مباركة ✅\n⚙️ لوحة تحكم المشرفين:", reply_markup=get_admin_keyboard(chat_id))

        elif data == "back_to_main":
            await show_main_menu(update, context)
    except Exception as e:
        print(f"Error handling callback: {e}")

async def handle_start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_main_menu(update, context)

async def handle_text_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.channel_post
    if not msg or not msg.text:
        return
    text = msg.text.strip()
    if text in ["إجازة", "اجازه", "اجازة", "قائمة", "القائمة"]:
        await show_main_menu(update, context)

# ----------------- خادم الويب -----------------
class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Bot is running successfully with complete chat isolation!")

    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()

def run_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), SimpleHandler)
    server.serve_forever()

def main():
    threading.Thread(target=run_server, daemon=True).start()

    app = (
        ApplicationBuilder()
        .token("8818665087:AAGFomHBBZmm3Kk1gbC-dYO3aJFuGzylW18")
        .concurrent_updates(20)
        .build()
    )

    app.add_handler(CommandHandler(["start", "show", "menu"], handle_start_command))
    app.add_handler(MessageHandler((filters.TEXT & ~filters.COMMAND), handle_text_messages))
    app.add_handler(CallbackQueryHandler(button_handler))

    print("البوت يعمل الآن بنجاح مع العزل الكامل لكل محادثة أو قناة...")
    app.run_polling()

if __name__ == "__main__":
    main()

