import os
import logging
import yt_dlp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, MessageHandler, filters, ContextTypes, CallbackQueryHandler

# Logging setup
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

video_data_store = {}

async def start_extraction(update: Update, context: ContextTypes.DEFAULT_TYPE):
    original_url = update.message.text
    if not original_url.startswith("http"):
        return

    chat_id = update.message.chat_id
    status_msg = await update.message.reply_text("Video details check karanawa... 🔎")

    try:
        ydl_opts = {'quiet': True, 'no_warnings': True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(original_url, download=False)
            formats = info.get('formats', [])
            
            m3u8_formats = {}
            mp4_formats = {}

            for f in formats:
                res = f.get('height')
                if not res: continue # Quality eka nathi ewa skip karanna

                # 1. m3u8 check kirima
                if 'm3u8' in f.get('protocol', '') or f.get('ext') == 'm3u8':
                    label = f"{res}p (m3u8)"
                    if label not in m3u8_formats:
                        m3u8_formats[label] = f.get('url')

                # 2. Direct MP4 check kirima (Video + Audio dekama thiyena ewa)
                elif f.get('vcodec') != 'none' and f.get('acodec') != 'none' and f.get('ext') == 'mp4':
                    label = f"{res}p (MP4)"
                    if label not in mp4_formats:
                        mp4_formats[label] = f.get('url')

            # Logic: m3u8 thiyenawanam ewa witharak gannawa, nathnam MP4 gannawa
            final_formats = {}
            if m3u8_formats:
                final_formats = m3u8_formats
                msg_text = "✅ m3u8 links labuna. Quality eka thoranna:"
            elif mp4_formats:
                final_formats = mp4_formats
                msg_text = "✅ m3u8 naha, direct MP4 links labuna. Quality eka thoranna:"
            else:
                await status_msg.edit_text("❌ Galapena links mukuth hoyaganna bari una.")
                return

            buttons = []
            for label, url in final_formats.items():
                # Quality eka witharak callback_data ekata yawamu (label eken quality eka gannawa)
                buttons.append([InlineKeyboardButton(label, callback_data=f"{chat_id}_{label}")])

            video_data_store[chat_id] = final_formats
            reply_markup = InlineKeyboardMarkup(buttons)
            await status_msg.edit_text(f"🎥 **Title:** {info.get('title')}\n\n{msg_text}", reply_markup=reply_markup)

    except Exception as e:
        await status_msg.edit_text(f"⚠️ Error: {str(e)}")

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data.split("_")
    chat_id = int(data[0])
    quality_label = data[1] # Meka dan "720p (m3u8)" wage label ekak

    if chat_id in video_data_store and quality_label in video_data_store[chat_id]:
        direct_link = video_data_store[chat_id][quality_label]
        await query.message.reply_text(f"✅ **Format:** {quality_label}\n\n**Link:**\n`{direct_link}`", parse_mode='Markdown')
    else:
        await query.message.reply_text("Aiyo... link eka expire wela. Aye try karanna.")

def main():
    TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
    if not TOKEN:
        raise SystemExit("TELEGRAM_TOKEN set karala naha")
    application = Application.builder().token(TOKEN).build()

    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, start_extraction))
    application.add_handler(CallbackQueryHandler(button_callback))

    print("Bot Active! m3u8 priority logic ekka...")
    application.run_polling()

if __name__ == '__main__':
    main()