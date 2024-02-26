import asyncio
import requests
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.utils import executor
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from telethon import TelegramClient


API_TOKEN = '6041655536:AAGrNVKK8PSWy3Em-FQlCYKT5zUO33bREpg'
VK_ACCESS_TOKEN = 'a4e86edea4e86edea4e86edeeba7ff283aaa4e8a4e86edec125d5322b959b7255f8d0e5'
api_id = 27460091
api_hash = '5edd552bb6d6e5d0f9d0f53adc3f0594'

bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)
logging_middleware = LoggingMiddleware()
dp.middleware.setup(logging_middleware)

client = TelegramClient('anon', api_id, api_hash)

class SearchState(StatesGroup):
    VK = State()
    TELEGRAM = State()
    TELEGRAM_CHANNEL = State()

async def search_vk_posts(keyword):
    try:
        search_url = f"https://api.vk.com/method/newsfeed.search?q={keyword}&count=5&access_token={VK_ACCESS_TOKEN}&v=5.131"
        response = requests.get(search_url).json()
        posts = response.get('response', {}).get('items', [])
        result_message = "Результаты поиска в ВК:\n"
        for post in posts:
            post_text = post.get('text', '')
            if len(post_text) > 100:
                post_text = post_text[:100] + '...'
            post_link = f"https://vk.com/wall{post['owner_id']}_{post['id']}"
            result_message += f"{post_text}\nСсылка на пост: {post_link}\n\n"
        return result_message if result_message else "По вашему запросу ничего не найдено."
    except Exception as e:
        return f"Произошла ошибка при поиске в ВК: {e}"

async def search_telegram_posts(keyword, channel_username):
    try:
        messages = []
        async with TelegramClient('anon', api_id, api_hash) as client:
            await client.start()
            async for message in client.iter_messages(channel_username, search=keyword, limit=5):
                if message.text:
                    messages.append(f"{message.text}\n")
            if messages:
                return "Результаты поиска в Telegram:\n" + "\n".join(messages)
            else:
                return "По вашему запросу сообщения не найдены."
    except Exception as e:
        return f"Произошла ошибка при поиске в Telegram: {e}"

@dp.message_handler(commands=['start'])
async def handle_start(message: types.Message):
    keyboard_markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    buttons = ['Искать в ВК', 'Искать в Telegram']
    keyboard_markup.add(*buttons)
    await message.reply("Привет! Я бот для поиска информации. Выберите, где вы хотите искать посты:", reply_markup=keyboard_markup)

@dp.message_handler(text='Искать в ВК')
async def handle_vk_search(message: types.Message):
    await message.reply("Введите ключевое слово для поиска в ВК:")
    await SearchState.VK.set()

@dp.message_handler(state=SearchState.VK)
async def handle_search_vk(message: types.Message, state: FSMContext):
    keyword = message.text
    search_result = await search_vk_posts(keyword)
    await message.reply(search_result[:4096], parse_mode='HTML')
    await state.finish()

@dp.message_handler(text='Искать в Telegram')
async def handle_telegram_search_query(message: types.Message):
    await message.reply("Введите имя канала для поиска в Telegram:")
    await SearchState.TELEGRAM_CHANNEL.set()

@dp.message_handler(state=SearchState.TELEGRAM_CHANNEL)
async def handle_telegram_channel(message: types.Message, state: FSMContext):
    channel_name = message.text
    await state.update_data(channel_name=channel_name)
    await message.reply("Введите ключевое слово для поиска в Telegram:")
    await SearchState.TELEGRAM.set()

@dp.message_handler(state=SearchState.TELEGRAM)
async def handle_search_telegram(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    channel_name = user_data['channel_name']
    keyword = message.text
    search_result = await search_telegram_posts(keyword, channel_name)
    await message.reply(search_result[:4096], parse_mode='HTML')
    await state.finish()

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)