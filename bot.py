from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
import os
import random
import threading
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# قاموس لتخزين حالة القائمة (مفتوحة/مغلقة) لكل قناة على حدة
channels_status = {}
# قاموس لتخزين قوائم الطلاب لكل قناة بشكل مستقل (المفتاح هو chat_id)
channels_students = {}

# أدعية متغيرة فاخرة ومباركة (تصميمك الأصلي)
duas = [
    "⊰💎⊱ رَبِّ أَعِنِّى وَلا تُعِنْ عَلَيَّ، وَانْصُرْنِي وَلا تَنْصُرْ عَلَيَّ ⊰💎⊱",
    "⊰🌺⊱ اللَّهُمَّ إِنِّي أَسْأَلُكَ العَفْوَ وَالعَافِيَةَ فِي الدُّنْيَا وَالآخِرَةِ ⊰🌺⊱",
    "⊰💎⊱ اللَّهُمَّ يَا مُقَلِّبَ القُلُوبِ ثَبِّتْ قَلْبِي عَلَى دِينِكَ ⊰💎⊱",
    "⊰🤲⊱ اللَّهُمَّ اجْعَلِ القُرْآنَ رَبِيعَ قُلُوبِنَا، وَنُورَ صُدُورِنَا ⊰🤲⊱",
]

# عبارات تحفيزية رسمية وعميقة عن أهل القرآن (تصميمك الأصلي)
motivations = [
    (
        "«أهل القرآن هم أهل الله وخاصته» — هنيئاً لمن اختاره الله ليحفظ كلامه في"
        " صدره."
    ),
    (
        "قال ابن مسعود رضي الله عنه: «ينبغي لحامل القرآن أن يُعرف بليله إذا"
        " الناس نهار، وبنومه إذا الناس سهار»."
    ),
    (
        "قال الإمام الشاطبي رحمه الله: «وفي الصدر قرآنٌ يورثُ صاحبه عِزّاً ومجدًا"
        " لا يُبارى»."
    ),
    (
        "حفظ القرآن في الصدر يورث خشية الله، ورفعة في الدارين، ونوراً يقذفه الله"
        " في قلب صاحبه."
    ),
    (
        "القرآن كنزٌ لا يفنى، وكلما بذلتَ له وقتك وعزيمتك، أعطاك من بركاته وأسراره."
    ),
]

def arabic_numerals(n):
    ar_digits = {"0": "٠", "1": "١", "2": "٢", "3": "٣", "4": "٤", "5": "٥", "6": "٦", "7": "٧", "8": "٨", "9": "٩"}
    return "".join(ar_digits.get(char, char) for char in str(n))

def get_hijri_date():
    now = datetime.now()
    days_diff = (now - datetime(2026, 6, 16)).days
    hijri_months = [
        ("محرم", 29),
        ("صفر", 30),
        ("ربيع الأول", 29),
        ("ربيع الآخر", 30),
        ("جمادى الأولى", 30),
        ("جمادى الآخرة", 29),
        ("رجب", 30),
        ("شعبان", 30),
        ("رمضان", 29),
        ("شوال", 30),
        ("ذو القعدة", 30),
        ("ذو الحجة", 29),
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
    return f"{arabic_numerals(h_day)} {h_month_name} {arabic_numerals(h_year)} هـ"

def get_current_date():
    now = datetime.now()
    days_ar = {
        "Sunday": "الأحد",
        "Monday": "الإثنين",
        "Tuesday": "الثلاثاء",
        "Wednesday": "الأربعاء",
        "Thursday": "الخميس",
        "Friday": "الجمعة",
        "Saturday": "السبت",
    }
    months_ar = {
        1: "يناير",
        2: "فبراير",
        3: "مارس",
        4: "أبريل",
        5: "مايو",
        6: "يونيو",
        7: "يوليو",
        8: "أغسطس",
        9: "سبتمبر",
        10: "أكتوبر",
        11: "نوفمبر",
        12: "ديسمبر",
    }

    day_name = days_ar.get(now.strftime("%A"), "")
    day_num = arabic_numerals(now.strftime("%d"))
    month_name = months_ar.get(now.month, "")
    year_num = arabic_numerals(now.strftime("%Y"))
    hijri_date = get_hijri_date()

    return f"• {day_name} {day_num} {month_name} {year_num} مـ — {hijri_date}"

def get_formatted_text(chat_id):
    is_open = channels_status.get(chat_id, True)
    status_text = "مفتوحة 🔓 🟢" if is_open else "مغلقة 🔒 🔴"
    
    selected_dua = random.choice(duas)
    selected_motivation = random.choice(motivations)

    slot_icons = [
        "👑", "🌹", "🕌", "🌼", "🕋", "🌺", "🍃", "🌟", "🕊", "📚", "🤲",
    ]

    chat_students = channels_students.get(chat_id, {})

    roles_text = ""
    for idx, (uid, data) in enumerate(chat_students.items(), 1):
        icon = slot_icons[(idx - 1) % len(slot_icons)]
        profile_link = f"<a href='tg://user?id={uid}'>{data['name']}</a>"
        formatted_idx = arabic_numerals(idx)
        roles_text += (
            f"{formatted_idx} {icon} ⃞ـ💎 {profile_link} — {data['riwaya']} {data['status']}\n"
        )

    if not roles_text:
        roles_text = "لا توجد أدوار مسجلة حتى الآن في هذه القناة، بادر بحجز دورك.\n"

    return f"""📚👑   <b>أكاديمية نور العلم للقراءة والإقراء والمتون العلمية</b>    👑📚
<u>{get_current_date()}</u>

🌺✨⌯⌲ {selected_motivation} ⌯⌲✨🌺

•🌺🕊 <b>حلقة الإجازة في حفظ القرآن الكريم بالقراءات العشر</b> 🌺🕊

• <b>حالة القائمة:</b> {status_text}
​༄ؘ ۪۪۫۫ ▹◃ ༄ؘ ۪۪۫۫━━━━━━━━━━━━━━༄ؘ ۪۪۫۫ ▹◃ ༄ؘ ۪۪۫۫
✨📝 <b>قائمة الأدوار:</b> 📝✨

{roles_text}
​༄ؘ ۪۪۫۫ ▹◃ ༄ؘ ۪۪۫۫━━━━━━━━━━━━━━༄ؘ ۪۪۫۫ ▹◃ ༄ؘ ۪۪۫۫
{selected_dua}"""

def get_channel_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💎 📝 أريد دور قراءة", callback_data="register_name")],
        [InlineKeyboardButton("❌ إزالة اسمي من القائمة", callback_data="delete_name")],
        [InlineKeyboardButton("⚙️ لوحة إعدادات المشرفين", callback_data="admin_main")],
    ])

def get_admin_keyboard(chat_id):
    is_open = channels_status.get(chat_id, True)
    toggle_text = "🔒 إغلاق القائمة مؤقتاً" if is_open else "🔓 فتح القائمة للتسجيل"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(toggle_text, callback_data="toggle_list")],
        [InlineKeyboardButton("✅ تعليم من أتم القراءة", callback_data="admin_mark_list")],
        [InlineKeyboardButton("🔄 تدوير وبدء قائمة جديدة", callback_data="reset_new_list")],
        [InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data="back_to_main")],
    ])

def get_mark_student_keyboard(chat_id):
    keyboard = []
    chat_students = channels_students.get(chat_id, {})
    for uid, data in chat_students.items():
        keyboard.append([InlineKeyboardButton(f"👤 {data['name']}", callback_data=f"mark_{uid}")])
    keyboard.append([InlineKeyboardButton("🔙 رجوع لوحة المشرفين", callback_data="admin_main")])
    return InlineKeyboardMarkup(keyboard)

riwayat_dict = {
    "نافع": ["قالون", "ورش"],
    "ابن كثير": [],
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

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    chat_id = query.message.chat.id if query else (update.message.chat.id if update.message else update.channel_post.chat.id)
    
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
    if not query:
        return

    chat_id = query.message.chat.id
    data = query.data
    user_id = query.from_user.id
    user_name = query.from_user.full_name

    if chat_id not in channels_status:
        channels_status[chat_id] = True
    if chat_id not in channels_students:
        channels_students[chat_id] = {}

    admin_actions = ["admin_main", "toggle_list", "reset_new_list", "admin_mark_list"]
    if data in admin_actions or data.startswith("mark_"):
        if not await is_user_admin(update, context):
            try:
                await query.answer("عذراً، هذا يخص المشرفين الأفاضل فقط ❌", show_alert=True)
            except Exception:
                pass
            return

    try:
        await query.answer()
    except Exception:
        pass

    try:
        if data == "admin_main":
            await query.message.edit_text("⚙️ لوحة تحكم المشرفين:", reply_markup=get_admin_keyboard(chat_id))
        elif data == "admin_mark_list":
            if not channels_students[chat_id]:
                await query.answer("القائمة فارغة تماماً!", show_alert=True)
            else:
                await query.message.edit_text("اختر الطالب لتعليم إتمامه القراءة:", reply_markup=get_mark_student_keyboard(chat_id))
        elif data.startswith("mark_"):
            target_uid = int(data.split("_")[1])
            if target_uid in channels_students[chat_id]:
                channels_students[chat_id][target_uid]["status"] = "✅"
                await show_main_menu(update, context)
        elif data == "register_name":
            if not channels_status[chat_id]:
                await query.answer("عذراً، باب التسجيل مغلق مؤقتاً 🔒", show_alert=True)
                return
            if user_id in channels_students[chat_id]:
                await query.answer("أنت مسجل بالفعل في هذه القائمة ⚠️", show_alert=True)
                return
            await query.message.edit_text("اختر الإمام الكريم لتحديد روايتك:", reply_markup=get_readers_keyboard())
        elif data == "delete_name":
            if user_id in channels_students[chat_id]:
                del channels_students[chat_id][user_id]
                await show_main_menu(update, context)
            else:
                await query.answer("عذراً، اسمك غير مسجل في القائمة أصلاً!", show_alert=True)
        elif data.startswith("reg_reader_"):
            reader_name = data.split("_")[2]
            if reader_name == "ابن كثير":
                channels_students[chat_id][user_id] = {"name": user_name, "riwaya": "ابن كثير", "status": "❓"}
                await show_main_menu(update, context)
            else:
                await query.message.edit_text(f"اختر الرواية أو الطريق عن الإمام {reader_name}:", reply_markup=get_riwayat_keyboard(reader_name))
        elif data.startswith("reg_riwaya_"):
            riwaya_name = data.split("_")[2]
            channels_students[chat_id][user_id] = {"name": user_name, "riwaya": riwaya_name, "status": "❓"}
            await show_main_menu(update, context)
        elif data == "toggle_list":
            channels_status[chat_id] = not channels_status[chat_id]
            is_open = channels_status[chat_id]
            status_msg = "🔒 **عذراً، تم إغلاق باب التسجيل في القائمة الآن.**" if not is_open else "🔓 **تم فتح باب التسجيل في القائمة، يمكنكم الآن حجز أدواركم.**"
            try:
                await query.message.chat.send_message(status_msg, parse_mode="Markdown")
            except Exception:
                pass
            await query.message.edit_text("⚙️ لوحة تحكم المشرفين:", reply_markup=get_admin_keyboard(chat_id))
        elif data == "reset_new_list":
            channels_students[chat_id].clear()
            await query.message.edit_text("تم بدء قائمة جديدة مباركة لهذه القناة ✅\n⚙️ لوحة تحكم المشرفين:", reply_markup=get_admin_keyboard(chat_id))
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

class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Bot is running successfully!")
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
        .token("8818665087:AAH18i0YqRZcrRPZ3j8-MFJuFdm2fjxCHNI")
        .build()
    )

    app.add_handler(CommandHandler(["start", "show", "menu"], handle_start_command))
    app.add_handler(MessageHandler((filters.TEXT & ~filters.COMMAND), handle_text_messages))
    app.add_handler(CallbackQueryHandler(button_handler))

    print("البوت يعمل الآن بنجاح...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()

