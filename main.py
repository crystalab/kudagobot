from telegram import InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, Filters, MessageHandler
import logging
import requests
import re

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
SEARCH_RADIUS_IN_METERS = 2500


def on_start(update, context):
    keyboard = [
        [InlineKeyboardButton("Рестораны", callback_data='restaurants'),
         InlineKeyboardButton("Клубы", callback_data='clubs')],
        [InlineKeyboardButton("Кино", callback_data='cinema'), InlineKeyboardButton("Парки", callback_data='park')],
        [InlineKeyboardButton("Бары", callback_data='bar'), InlineKeyboardButton("Театры", callback_data='theatre')]
    ]

    context.bot.send_message(chat_id=update.effective_chat.id,
                             text='Куда вы хотите сходить?',
                             reply_markup=InlineKeyboardMarkup(keyboard))


def on_place_type_chosen(update, context):
    query = update.callback_query
    query.answer()

    context.user_data['place_type'] = query.data
    context.bot.send_message(chat_id=update.effective_chat.id, text='Где мне искать?')


def on_place_chosen(update, context):
    query = update.callback_query
    query.answer()

    place_id = query.data
    response = requests.get(f'https://kudago.com/public-api/v1.4/places/{place_id}/')
    data = response.json()

    title = data['title']
    address = data['address']
    timetable = data['timetable']
    description = re.sub('<[^<]+?>', '', data['description'])

    media = []
    for image in data['images'][:3]:
        media.append(InputMediaPhoto(image['image']))

    context.bot.send_message(chat_id=update.effective_chat.id, parse_mode='HTML',
                             text=f'{title}\n{address}\n{timetable}\n{description}')
    context.bot.send_media_group(chat_id=update.effective_chat.id, media=media)


def on_location(update, context):
    location = update.message.location
    context.user_data['lon'] = location.longitude
    context.user_data['lat'] = location.latitude

    params = {'radius': SEARCH_RADIUS_IN_METERS,
              'page_size': 5,
              'categories': context.user_data['place_type'],
              'lon': context.user_data['lon'],
              'lat': context.user_data['lat']}

    response = requests.get('https://kudago.com/public-api/v1.4/places/', params=params)
    data = response.json()

    if data['count'] == 0:
        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text='Я не смог ничего найти, попробуйте другой адрес')
        return

    keyboard = []
    for result in data['results']:
        col = InlineKeyboardButton(result['title'], callback_data=result['id'])
        row = [col]
        keyboard.append(row)

    context.bot.send_message(chat_id=update.effective_chat.id,
                             text='Вот, что мне удалось найти:',
                             reply_markup=InlineKeyboardMarkup(keyboard))


def main():
    token = '1245728204:AAHJNUqP1yjD92VMNFnStuxSvgYQcvtoRWw'
    proxy = 'http://guest:guestguest@37.143.12.130:3128/'
    updater = Updater(token=token, use_context=True, request_kwargs={'proxy_url': proxy})
    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler('start', on_start))
    dispatcher.add_handler(CallbackQueryHandler(on_place_type_chosen, pattern='^[a-z]+$'))
    dispatcher.add_handler(CallbackQueryHandler(on_place_chosen, pattern='^\d+$'))
    dispatcher.add_handler(MessageHandler(Filters.location, on_location))

    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
