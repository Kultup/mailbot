import asyncio
import imaplib
import email
import logging
from telegram import Bot
from telegram.error import TelegramError
import os
from dotenv import load_dotenv


load_dotenv()


logging.basicConfig(filename='bot.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', encoding='utf-8')

imap_server = 'imap.gmail.com'
imap_port = 993
imap_user = os.getenv('IMAP_USER')
imap_password = os.getenv('IMAP_PASSWORD')

telegram_bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID')

TEMP_FOLDER = 'attachments/'

async def send_telegram_message(text, attachment=None):
    try:
        bot = Bot(token=telegram_bot_token)
        if attachment:
            if attachment['type'] == 'image':
                with open(attachment['path'], 'rb') as file:
                    await bot.send_photo(chat_id=telegram_chat_id, photo=file, caption=text)
            else:
                with open(attachment['path'], 'rb') as file:
                    await bot.send_document(chat_id=telegram_chat_id, document=file, caption=text)
        else:
            await bot.send_message(chat_id=telegram_chat_id, text=text, parse_mode='Markdown')

        logging.info("Повідомлення успішно відправлено в Telegram.")
    except TelegramError as e:
        logging.error(f"Помилка при відправці повідомлення в Telegram: {e}")
    except Exception as e:
        logging.error(f"Невідома помилка при відправці повідомлення в Telegram: {str(e)}")


def extract_body_and_attachments(msg):
    body = ""
    attachments = []
    
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition"))

            if content_type == "text/plain" and "attachment" not in content_disposition:
                body = part.get_payload(decode=True).decode(part.get_content_charset(), errors='ignore')
            
            elif "attachment" in content_disposition:
                filename = part.get_filename()
                if filename:
                   
                    if not os.path.exists(TEMP_FOLDER):
                        os.makedirs(TEMP_FOLDER)
                    filepath = os.path.join(TEMP_FOLDER, filename)
                    with open(filepath, 'wb') as f:
                        f.write(part.get_payload(decode=True))
                    attachments.append({'type': 'file', 'path': filepath, 'filename': filename})
                
           
            elif content_type.startswith("image"):
                filename = part.get_filename()
                if filename:
                    if not os.path.exists(TEMP_FOLDER):
                        os.makedirs(TEMP_FOLDER)
                    filepath = os.path.join(TEMP_FOLDER, filename)
                    with open(filepath, 'wb') as f:
                        f.write(part.get_payload(decode=True))
                    attachments.append({'type': 'image', 'path': filepath, 'filename': filename})
    
    else:
        body = msg.get_payload(decode=True).decode(msg.get_content_charset(), errors='ignore')

   
    if "This is a notification that a contact form was submitted" in body:
        body = body.split("This is a notification that a contact form was submitted")[0].strip()

    return body, attachments

async def check_mail():
    try:
        mail = imaplib.IMAP4_SSL(imap_server)
        mail.login(imap_user, imap_password)
        mail.select('inbox')

    
        senders = ["wordpress@krainamriy.fun", "no-reply@uployal.io", "email@krainamriy.fun"]
        mail_ids = []

        for sender in senders:
            status, data = mail.search(None, f'(UNSEEN FROM "{sender}")')
            if status == 'OK':
                mail_ids.extend(data[0].split())

        if not mail_ids:
            logging.info("Немає нових листів від вказаних відправників.")
            return

        for num in mail_ids:
            status, data = mail.fetch(num, '(RFC822)')
            if status != 'OK':
                logging.error(f"Помилка при отриманні листа з ID {num}")
                continue

            msg = email.message_from_bytes(data[0][1])

          
            body, attachments = extract_body_and_attachments(msg) 

           
            message = f"""
📬 *Повідомлення*:
{body}
"""

           
            if attachments:
                for attachment in attachments:
                    await send_telegram_message(message, attachment)
            else:
                await send_telegram_message(message)

        mail.close()
        mail.logout()
    except imaplib.IMAP4.error as e:
        logging.error(f"Помилка з підключенням до пошти: {str(e)}")
    except Exception as e:
        logging.error(f"Невідома помилка при перевірці пошти: {str(e)}")


async def main():
    while True:
        try:
            await check_mail() 
        except Exception as e:
            logging.error(f"Загальна помилка: {str(e)}")
        await asyncio.sleep(300)  


if __name__ == '__main__':
    asyncio.run(main())
