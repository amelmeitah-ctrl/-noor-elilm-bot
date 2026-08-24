from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
import os
import random
import threading
from telegram import KeyboardButton, ReplyKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

list_is_open = True
students_list = {}

duas = [
    "⊰💎⊱ رَبِّ أَعِنِّى وَلا تُعِنْ عَلَيَّ، وَانْصُرْنِي وَلا تَنْصُرْ عَلَيَّ ⊰💎⊱",
    "⊰🌺⊱ اللَّهُمَّ إِنِّي أَسْأَلُكَ العَفْوَ وَالعَافِيَةَ فِي الدُّنْيَا وَالآخِرَةِ ⊰🌺⊱",
    "⊰💎⊱ اللَّهُمَّ يَا مُقَلِّبَ القُلُوبِ ثَبِّتْ قَلْبِي عَلَى دِينِكَ ⊰💎⊱",
    "⊰🤲⊱ اللَّهُمَّ اجْعَلِ القُرْآنَ رَبِيعَ قُلُوبِنَا، وَنُورَ صُدُورِنَا ⊰🤲⊱",
]

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
  return f"{h_day} {h_month_name} {h_year} هـ"


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
  day_num = now.strftime("%d")
  month_name = months_ar.get(now.month, "")
  year_num = now.strftime("%Y")
  hijri_date = get_hijri_date()

  return f"• {day_name} {day_num} {month_name} {year_num} مـ — {hijri_date}"


def get_formatted_text():
  status_text = "مفتوحة 🔓 🟢" if list_is_open else "مغلقة 🔒 🔴"
  selected_dua = random.choice(duas)
  selected_motivation = random.choice(motivations)

  slot_icons = [
      "👑",
      "🌹",
      "🕌",
      "🌼",
      "🕋",
      "🌺",
      "🍃",
      "🌟",
      "🕊",
      "📚",
      "🤲",
  ]

  roles_text = ""
  for idx, (uid, data) in enumerate(students_list.items(), 1):
    icon = slot_icons[(idx - 1) % len(slot_icons)]
    profile_link = f"<a href='tg://user?id={uid}'>{data['name']}</a>"
    roles_text += (
        f"{idx} {icon} ⃞ـ💎 {profile_link} — {data['riwaya']} {data['status']}\n"
    )

  if not roles_text:
    roles_text = "لا توجد أدوار مسجلة حتى الآن، بادر بحجز دورك.\n"

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


# دقة بناء الأزرار مع تمرير خصائص الألوان بالطريقة الصحيحة عبر api_kwargs
def get_colored_reply_keyboard():
  toggle_text = "🔓 فتح القائمة" if not list_is_open else "🔒 إغلاق القائمة"
  toggle_style = {"bg_primary": True} if not list_is_open else {"bg_danger": True}

  keyboard = [
      [
          KeyboardButton(
              "📝 سجّلي اسمي", api_kwargs={"style": {"bg_primary": True}}
          ),  # أزرق
          KeyboardButton(
              "❌ احذفي اسمي", api_kwargs={"style": {"bg_danger": True}}
          ),  # أحمر
      ],
      [
          KeyboardButton(
              "✅ قرأتُ", api_kwargs={"style": {"bg_success": True}}
          )  # أخضر
      ],
      [
          KeyboardButton(toggle_text, api_kwargs={"style": toggle_style})
      ],  # يتغير لونه حسب الحالة
      [KeyboardButton("📋 عرض القائمة")],
  ]
  return ReplyKeyboardMarkup(
      keyboard, resize_keyboard=True, is_persistent=True
  )


async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
  text = get_formatted_text()
  reply_markup = get_colored_reply_keyboard()

  target_message = update.message or update.channel_post
  if target_message:
    await target_message.reply_text(
        text, parse_mode="HTML", reply_markup=reply_markup
    )


async def handle_text_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
  global list_is_open
  msg = update.message
  if not msg or not msg.text:
    return
  text = msg.text.strip()
  user_id = msg.from_user.id
  user_name = msg.from_user.full_name

  if text in ["إجازة", "اجازه", "اجازة", "📋 عرض القائمة"]:
    await show_main_menu(update, context)

  elif text == "📝 سجّلي اسمي":
    if not list_is_open:
      await msg.reply_text("عذراً، باب التسجيل مغلق مؤقتاً 🔒")
      return
    if user_id in students_list:
      await msg.reply_text("أنت مسجل بالفعل في هذه القائمة ⚠️")
      return
    students_list[user_id] = {
        "name": user_name,
        "riwaya": "حفص عن عاصم",
        "status": "❓",
    }
    await show_main_menu(update, context)

  elif text == "❌ احذفي اسمي":
    if user_id in students_list:
      del students_list[user_id]
      await show_main_menu(update, context)
    else:
      await msg.reply_text("عذراً، اسمك غير مسجل في القائمة أصلاً!")

  elif text == "✅ قرأتُ":
    if user_id in students_list:
      students_list[user_id]["status"] = "✅"
      await show_main_menu(update, context)
    else:
      await msg.reply_text("اسمك غير موجود في القائمة لتعديله!")

  elif text in ["🔒 إغلاق القائمة", "🔓 فتح القائمة"]:
    list_is_open = not list_is_open
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
      .token("8818665087:AAGPBN9ODdoBjwl4LtVcfWrHdQJQO8HrNrY")
      .build()
  )

  app.add_handler(CommandHandler(["start", "show", "menu"], show_main_menu))
  app.add_handler(
      MessageHandler((filters.TEXT & ~filters.COMMAND), handle_text_messages)
  )

  print("البوت يعمل الآن بأزرار ملونة صحيحة...")
  app.run_polling()


if __name__ == "__main__":
  main()
