import telebot
from bs4 import BeautifulSoup
import requests
import html
from urllib.parse import urlparse
import os

# Получаем токен из переменной окружения
BOT_TOKEN = os.getenv('BOT_TOKEN')
bot = telebot.TeleBot(BOT_TOKEN)

def clean_html(html_content):
    """Очищает HTML от ненужных элементов и стилей"""
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Удаляем ненужные теги
    for tag in soup.find_all(['script', 'style', 'iframe', 'nav', 'footer', 'header']):
        tag.decompose()
    
    # Удаляем все классы и ID
    for tag in soup.find_all(True):
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
        
        # Очищаем HTML
        clean_content = clean_html(str(article))
        
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
Просто отправь мне ссылку на статью, и я верну её в формате, готовом для вставки в WordPress.

Примечание: для некоторых сайтов может потребоваться дополнительная настройка парсера.
    """
    bot.reply_to(message, welcome_text)

@bot.message_handler(func=lambda message: True)
def handle_url(message):
    try:
        url = message.text.strip()
        # Проверяем, является ли сообщение ссылкой
        result = urlparse(url)
        if all([result.scheme, result.netloc]):
            bot.reply_to(message, "Начинаю парсинг статьи...")
            content = parse_article(url)
            # Отправляем результат частями, если он слишком длинный
            max_length = 4096
            for i in range(0, len(content), max_length):
                chunk = content[i:i + max_length]
                bot.reply_to(message, chunk)
        else:
            bot.reply_to(message, "Пожалуйста, отправьте корректную ссылку на статью.")
    except Exception as e:
        bot.reply_to(message, f"Произошла ошибка: {str(e)}")

# Запускаем бота
if __name__ == "__main__":
    bot.polling(none_stop=True)
