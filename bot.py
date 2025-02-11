import telebot
from bs4 import BeautifulSoup
import requests
import html
from urllib.parse import urlparse, urljoin
import os
import time
import base64
from io import BytesIO

# Получаем токен из переменной окружения
BOT_TOKEN = os.getenv('BOT_TOKEN')
bot = telebot.TeleBot(BOT_TOKEN)

def download_image(img_url, base_url):
    """Скачивает изображение и возвращает его в base64"""
    try:
        # Формируем полный URL изображения
        full_url = urljoin(base_url, img_url)
        
        # Скачиваем изображение
        response = requests.get(full_url, timeout=10)
        response.raise_for_status()
        
        # Определяем тип изображения из заголовков
        content_type = response.headers.get('content-type', 'image/jpeg')
        
        # Кодируем изображение в base64
        img_base64 = base64.b64encode(response.content).decode('utf-8')
        
        return f"data:{content_type};base64,{img_base64}"
    except Exception as e:
        print(f"Ошибка при скачивании изображения {img_url}: {str(e)}")
        return img_url

def clean_html(html_content, base_url):
    """Очищает HTML и обрабатывает изображения"""
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Удаляем ненужные теги
    for tag in soup.find_all(['script', 'style', 'iframe', 'nav', 'footer', 'header']):
        tag.decompose()
    
    # Обрабатываем все изображения
    for img in soup.find_all('img'):
        src = img.get('src')
        if src:
            # Пропускаем data:image и внешние ссылки на популярные CDN
            if not (src.startswith('data:') or 'wp-content' in src or 'wp-includes' in src):
                try:
                    new_src = download_image(src, base_url)
                    img['src'] = new_src
                except Exception as e:
                    print(f"Ошибка обработки изображения: {str(e)}")
    
    # Очищаем ненужные атрибуты, сохраняя src для изображений
    for tag in soup.find_all(True):
        if tag.name == 'img':
            src = tag.get('src')
            alt = tag.get('alt')
            tag.attrs = {'src': src}
            if alt:
                tag['alt'] = alt
        else:
            tag.attrs = {}
    
    return str(soup)

def parse_article(url):
    """Парсит статью по URL"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Находим основной контент
        article = (
            soup.find('article') or 
            soup.find('main') or 
            soup.find('div', class_='content') or 
            soup.find('div', class_='post-content') or
            soup.find('div', class_='entry-content')
        )
        
        if not article:
            return "Не удалось найти контент статьи. Попробуйте другой сайт или обратитесь к разработчику для настройки парсера под этот сайт."
        
        # Очищаем HTML и обрабатываем изображения
        clean_content = clean_html(str(article), url)
        
        # Форматируем контент для WordPress
        formatted_content = f"""
        <!-- wp:html -->
        {clean_content}
        <!-- /wp:html -->
        """
        
        return formatted_content
        
    except Exception as e:
        return f"Ошибка при парсинге: {str(e)}"

@bot.message_handler(commands=['start'])
def send_welcome(message):
    welcome_text = """
Привет! Я помогу спарсить статью для WordPress.
Просто отправь мне ссылку на статью, и я верну её в формате HTML-файла, готового для вставки в WordPress.

Особенности:
- Сохраняю изображения в base64 формате
- Отправляю результат одним файлом
- Сохраняю форматирование статьи
    """
    bot.reply_to(message, welcome_text)

@bot.message_handler(func=lambda message: True)
def handle_url(message):
    try:
        url = message.text.strip()
        # Проверяем, является ли сообщение ссылкой
        result = urlparse(url)
        if all([result.scheme, result.netloc]):
            processing_msg = bot.reply_to(message, "Начинаю парсинг статьи...")
            
            # Парсим статью
            content = parse_article(url)
            
            # Создаем временный файл
            timestamp = int(time.time())
            filename = f"article_{timestamp}.html"
            
            # Отправляем файл
            bio = BytesIO(content.encode('utf-8'))
            bio.name = filename
            bot.send_document(message.chat.id, bio, caption="Готово! Вставьте содержимое этого файла в HTML-редактор WordPress.")
            
            # Удаляем сообщение о процессе
            bot.delete_message(message.chat.id, processing_msg.message_id)
            
        else:
            bot.reply_to(message, "Пожалуйста, отправьте корректную ссылку на статью.")
    except Exception as e:
        bot.reply_to(message, f"Произошла ошибка: {str(e)}")

# Запускаем бота
if __name__ == "__main__":
    bot.polling(none_stop=True)
