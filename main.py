import random
import time
from dotenv import load_dotenv
import telebot
import os
import requests
from telebot import types
import threading


load_dotenv()
WEATHER_KEY = os.getenv("WEATHERAPI_ACCESS_TOKEN")
API_KEY = os.getenv("TELEGRAM_ACCESS_TOKEN")
bot = telebot.TeleBot(API_KEY, parse_mode=None)

users = {}


fields = ['пшениця', 'рис', 'соняшник']
animals = {
    'курка': {'resource': 'яйця', 'price': 50, 'stall_needed': 'курник', 'amount': 0},
    'корова': {'resource': 'молоко', 'price': 100, 'stall_needed': 'корівник', 'amount': 0}
}


class User:
    def __init__(self, user_id):
        self.user_id = user_id
        self.city = None
        self.coins = 500
        self.fields = 0
        self.field_crops = {}
        self.animals = {'курка': 0, 'корова': 0}
        self.stalls = {'курник': 0, 'корівник': 0}
        self.dogs = 0
        self.resources = {
            'яйця': 0,
            'молоко': 0,
            'рис': 0,
            'соняшник': 0,
            'пшениця': 0,
            'насіння_рису': 0,
            'насіння_соняшнику': 0,
            'насіння_пшениці': 0
        }
        self.threads = {'курка': None, 'корова': None}
        self.attack_thread = None

    def set_location(self, city):
        url = f"http://api.weatherapi.com/v1/current.json?key={WEATHER_KEY}&q={city}&aqi=no"
        response = requests.get(url)
        data = response.json()
        if response.status_code != 200:
            return "Не вдалося отримати дані про погоду. Перевірте правильність написання назви міста."
        else:
            self.city = city
            return f"Ваше місцезнаходження було оновлено на {city}."

    def buy_stall(self, animal_type):
        stall_needed = animals[animal_type]['stall_needed']
        if stall_needed == 'курник':
            price = 150
        else:
            price = 200
        if self.coins >= price:
            self.coins -= price
            if self.stalls[stall_needed] < 5:
                self.stalls[stall_needed] += 1
                return f"Ви купили новий {stall_needed} рівень!"
            else:
                return f"Ви вже маєте максимальний рівень для {stall_needed}."
        else:
            return f"Не вистачає монет для покупки {stall_needed}!"

    def expand_stall(self, animal_type):
        stall_needed = animals[animal_type]['stall_needed']
        if self.stalls[stall_needed] > 0 and self.coins >= 100:
            self.coins -= 100
            self.stalls[stall_needed] += 1
            return f"Ви розширили {stall_needed} на 1 рівень!"
        return "Не вистачає монет для розширення загону або у вас немає місця для розширення!"

    def start_animal_thread(self, animal_type):
        if self.threads[animal_type] is None or not self.threads[animal_type].is_alive():
            self.threads[animal_type] = threading.Thread(target=simulate_animal_production, args=(self, animal_type))
            self.threads[animal_type].start()

    def start_bear_attack_thread(self):
        if self.attack_thread is None or not self.attack_thread.is_alive():
            self.attack_thread = threading.Thread(target=simulate_bear_attack, args=(self,))
            self.attack_thread.start()

    def buy_field(self):
        if self.fields < 8 and self.coins >= 100:
            self.fields += 1
            return "Ви купили нове поле!"
        return "Не вистачає монет або ви досягли максимуму полів!"

    def plant_crop(self, field, crop):
        if field > self.fields or field <= 0:
            return "Це поле не існує!"
        if field in self.field_crops:
            return f"Поле {field} вже засіяне!"
        if crop == 'пшениця' and self.resources['насіння_пшениці'] <= 0:
            return "У вас немає насіння пшениці!"
        if crop == 'рис' and self.resources['насіння_рису'] <= 0:
            return "У вас немає насіння рису!"
        if crop == 'соняшник' and self.resources['насіння_соняшнику'] <= 0:
            return "У вас немає насіння соняшнику!"
        if crop not in fields:
            return "Невідомий тип культури!"
        if crop == 'пшениця':
            self.resources['насіння_пшениці'] -= 1
        elif crop == 'рис':
            self.resources['насіння_рису'] -= 1
        elif crop == 'соняшник':
            self.resources['насіння_соняшнику'] -= 1

        self.field_crops[field] = crop
        return f"Ви посіяли {crop} на полі {field}."

    def harvest(self):
        harvested_wheat = 0
        harvested_rice = 0
        harvested_sunflower = 0
        harvested_eggs = 0
        harvested_milk = 0

        for field, crop in self.field_crops.items():
            if crop == 'пшениця':
                harvested_wheat += random.randint(1, 3)
            elif crop == 'рис':
                harvested_rice += random.randint(1, 3)
            elif crop == 'соняшник':
                harvested_sunflower += random.randint(1, 2)
        if self.animals['курка'] > 0:
            harvested_eggs = random.randint(1, self.animals['курка'] * 2)
        else:
            harvested_eggs = 0

        if self.animals['корова'] > 0:
            harvested_milk = random.randint(1, self.animals['корова'] * 2)
        else:
            harvested_milk = 0

        self.resources['пшениця'] += harvested_wheat
        self.resources['рис'] += harvested_rice
        self.resources['соняшник'] += harvested_sunflower
        self.resources['яйця'] += harvested_eggs
        self.resources['молоко'] += harvested_milk

        return (f"Ви зібрали врожай: {harvested_wheat} пшениці, "
                f"\n{harvested_rice} рису, {harvested_sunflower} \n"
                f"соняшника, {harvested_eggs} яєць, {harvested_milk} молока!")

    def get_status(self):
        return (f"Баланс: {self.coins} монет"
                f"\nПоля: {self.fields}/8"
                f"\nКур: {self.animals['курка']} шт."
                f"\nКорів: {self.animals['корова']} шт."
                f"\nЯйця: {self.resources['яйця']} шт."
                f"\nМолоко: {self.resources['молоко']} шт."
                f"\nРис: {self.resources['рис']} шт."
                f"\nСоняшник: {self.resources['соняшник']} шт."
                f"\nПшениця: {self.resources['пшениця']} шт."
                f"\nСобаки: {self.dogs} шт."
                f"\nЗагони: Курник: {self.stalls['курник']} рівень, Корівник: {self.stalls['корівник']} рівень")

    def buy_animal(self, animal):
        if animal in animals:
            stall_needed = animals[animal]['stall_needed']
            if self.stalls[stall_needed] > 0:
                price = animals[animal]['price']
                if self.coins >= price:
                    self.coins -= price
                    self.animals[animal] += 1
                    bot.send_message(self.user_id, f"Ви купили {animal}!")
                    if self.threads[animal] is None or not self.threads[animal].is_alive():
                        self.threads[animal] = threading.Thread(target=simulate_animal_production, args=(self, animal))
                        self.threads[animal].start()
                    return f"Ви купили {animal}!"
                return "Не вистачає монет!"
            return f"Не вистачає місця для {animal}!"
        return "Невідомий тип тварини!"

    def buy_dog(self):
        if self.coins >= 150:
            self.coins -= 150
            self.dogs += 1
            return "Ви купили собаку!"
        return "Не вистачає монет для покупки собаки!"

    def sell_resource(self, resource, amount):
        resource_prices = {
            'яйця': 10,
            'молоко': 15,
            'пшениця': 5,
            'рис': 6,
            'соняшник': 8
        }
        if self.resources.get(resource, 0) >= amount:
            price_per_unit = resource_prices.get(resource, 0)
            total_earnings = price_per_unit * amount
            self.resources[resource] -= amount
            self.coins += total_earnings
            return f"Ви продали {amount} {resource} за {total_earnings} монет!"
        return f"Не вистачає {resource} для продажу!"


def get_or_create_user(user_id):
    if user_id not in users:
        users[user_id] = User(user_id)
    return users[user_id]


@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.chat.id
    if user_id not in users:
        bot.send_message(user_id, "Вітаю! Ви отримали 500 монет.", reply_markup=show_menu(message))
    else:
        bot.send_message(user_id, "Вітаю знову!", reply_markup=show_menu(message))


@bot.callback_query_handler(func=lambda call: call.data == 'show_menu')
def show_menu(call):
    bot.send_photo(call.chat.id, 'https://img.freepik.com/free-vector/cartoon-style-farm-illustration_52683-82399.jpg?t=st=1731266962~exp=1731270562~hmac=12ae12ce1510e949c5cdc69175064008320f992bb3e06ee9d5f204fb99577097&w=1480')
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton('Купити поле', callback_data='buy_field'),
        types.InlineKeyboardButton('Купити тварину', callback_data='buy_animal'),
        types.InlineKeyboardButton('Зібрати врожаї', callback_data='harvest'),
        types.InlineKeyboardButton('Перевірити стан', callback_data='check_status'),
        types.InlineKeyboardButton('Купити собаку', callback_data='buy_dog'),
        types.InlineKeyboardButton('Продати ресурси', callback_data='sell_resources'),
        types.InlineKeyboardButton('Купити насіння', callback_data='buy_seeds'),
        types.InlineKeyboardButton('Купити або розширити загін', callback_data='buy_stall'),
        types.InlineKeyboardButton('Посадити культуру', callback_data='plant_crop'),
        types.InlineKeyboardButton('Перемістити розміщення ферми', callback_data='set_location'),
    )
    bot.send_message(call.chat.id, "Оберіть дію:", reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data == 'buy_field')
def buy_field(call):
    bot.send_photo(call.message.chat.id, "https://img.freepik.com/free-vector/blank-nature-park-landscape-daytime-scene-with-pathway-through-meadow_1308-56553.jpg?t=st=1731267156~exp=1731270756~hmac=3c5acdce2769ee3198bd067ea209fd69fff960a36522f7c9e7dd391297b2e004&w=1380")
    user = get_or_create_user(call.from_user.id)
    result = user.buy_field()
    bot.send_message(call.message.chat.id, result)
    show_menu(call.message)


def simulate_bear_attack(user):
    while True:
        time.sleep(3600)
        if user.dogs > 0:
            bot.send_photo(user.user_id, "https://img.freepik.com/free-vector/hand-drawn-cartoon-german-shepherd-illustration_23-2150435973.jpg?t=st=1731268027~exp=1731271627~hmac=7dafae435d8a417673e5430ea217c022d908d3cc9b5c2ded60b9bf1a0d02eb7c&w=740")
            user.dogs -= 1
            bot.send_message(user.user_id, "Ваш собака захистив тварин, але загинув при цьому.")
        else:
            bot.send_photo(user.user_id, "https://img.freepik.com/free-vector/brown-bear-nature-scene_1308-27985.jpg?t=st=1731267710~exp=1731271310~hmac=581836f6e4303f9b178e8b2486ac9124b22698a49b931afb1bb00ecc4dbb5b88&w=996")
            if user.animals['курка'] > 0:
                user.animals['курка'] -= 1
                bot.send_message(user.user_id, "Ведмідь напав і забрав 1 курку!")
            elif user.animals['корова'] > 0:
                user.animals['корова'] -= 1
                bot.send_message(user.user_id, "Ведмідь напав і забрав 1 корову!")
            else:
                bot.send_message(user.user_id, "Ведмідь намагався напасти, але у вас немає тварин для атаки.")
        time.sleep(3600)


@bot.callback_query_handler(func=lambda call: call.data == 'buy_animal')
def buy_animal(call):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton('Купити курку', callback_data='buy_chicken'),
        types.InlineKeyboardButton('Купити корову', callback_data='buy_cow')
    )
    bot.send_message(call.message.chat.id, "Оберіть тварину для покупки:", reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data == 'buy_chicken')
def buy_chicken(call):
    user = get_or_create_user(call.from_user.id)
    result = user.buy_animal('курка')
    bot.send_message(call.message.chat.id, result)
    show_menu(call.message)


@bot.callback_query_handler(func=lambda call: call.data == 'buy_cow')
def buy_cow(call):
    user = get_or_create_user(call.from_user.id)
    result = user.buy_animal('корова')
    bot.send_message(call.message.chat.id, result)
    show_menu(call.message)


weather_cache = {}


def get_weather(city):
    current_time = time.time()
    if city in weather_cache and current_time - weather_cache[city]['timestamp'] < 6800:
        return weather_cache[city]['data']
    url = f"http://api.weatherapi.com/v1/current.json?key={WEATHER_KEY}&q={city}&aqi=no"
    try:
        response = requests.get(url)
        data = response.json()
        if 'error' in data:
            return None
    except requests.exceptions.RequestException as e:
        print(f"Помилка з зібранням даних про погоду: {e}")
        return None


@bot.callback_query_handler(func=lambda call: call.data == 'set_location')
def set_location(call):
    user = get_or_create_user(call.from_user.id)
    bot.send_message(call.message.chat.id, "Введіть місто для визначення погоди:")
    bot.register_next_step_handler(call.message, process_location)


def process_location(message):
    user = get_or_create_user(message.from_user.id)
    city = message.text.strip()
    result = user.set_location(city)
    bot.send_message(message.chat.id, result)
    show_menu(message)


@bot.callback_query_handler(func=lambda call: call.data == 'check_status')
def check_status(call):
    user = get_or_create_user(call.from_user.id)
    bot.send_message(call.message.chat.id, user.get_status())
    show_menu(call.message)


@bot.callback_query_handler(func=lambda call: call.data == 'buy_dog')
def buy_dog(call):
    user = get_or_create_user(call.from_user.id)
    result = user.buy_dog()
    bot.send_message(call.message.chat.id, result)
    show_menu(call.message)


@bot.callback_query_handler(func=lambda call: call.data == 'sell_resources')
def sell_resources(call):
    bot.send_photo(call.message.chat.id, "https://img.freepik.com/free-vector/outdoor-farm-market-stalls-wooden-fair-booths-kiosks-with-striped-awning-farmer-food-honey-dairy-products-vegetables-wood-vendor-counters-street-trading-cartoon-vector-illustration_107791-10531.jpg?t=st=1731268089~exp=1731271689~hmac=6ab80b18eca022461a67269013de30bd4647726d11e09130f212b6eb64ba6033&w=1380")
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton('Продати яйця', callback_data='sell_eggs'),
        types.InlineKeyboardButton('Продати молоко', callback_data='sell_milk'),
        types.InlineKeyboardButton('Продати пшеницю', callback_data='sell_wheat'),
        types.InlineKeyboardButton('Продати рис', callback_data='sell_rice'),
        types.InlineKeyboardButton('Продати соняшник', callback_data='sell_sunflower')
    )
    bot.send_message(call.message.chat.id, "Оберіть ресурс для продажу:", reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data == 'sell_eggs')
def sell_eggs(call):
    user = get_or_create_user(call.from_user.id)
    result = user.sell_resource('яйця', 1)
    bot.send_message(call.message.chat.id, result)
    show_menu(call.message)


@bot.callback_query_handler(func=lambda call: call.data == 'sell_milk')
def sell_milk(call):
    user = get_or_create_user(call.from_user.id)
    result = user.sell_resource('молоко', 1)
    bot.send_message(call.message.chat.id, result)
    show_menu(call.message)


@bot.callback_query_handler(func=lambda call: call.data == 'sell_wheat')
def sell_wheat(call):
    user = get_or_create_user(call.from_user.id)
    result = user.sell_resource('пшениця', 1)
    bot.send_message(call.message.chat.id, result)
    show_menu(call.message)


@bot.callback_query_handler(func=lambda call: call.data == 'sell_rice')
def sell_rice(call):
    user = get_or_create_user(call.from_user.id)
    result = user.sell_resource('рис', 1)
    bot.send_message(call.message.chat.id, result)
    show_menu(call.message)


@bot.callback_query_handler(func=lambda call: call.data == 'sell_sunflower')
def sell_sunflower(call):
    user = get_or_create_user(call.from_user.id)
    result = user.sell_resource('соняшник', 1)
    bot.send_message(call.message.chat.id, result)
    show_menu(call.message)


@bot.callback_query_handler(func=lambda call: call.data == 'harvest')
def harvest(call):
    bot.send_photo(call.message.chat.id, "https://img.freepik.com/free-vector/background-scene-with-stack-hays-field_1308-42341.jpg?t=st=1731267336~exp=1731270936~hmac=501a1aa7b55801b18f8eb1456e30dc08ad4ff73faa75609d85fac1c73f605510&w=1380")
    user = get_or_create_user(call.from_user.id)
    result = user.harvest()
    bot.send_message(call.message.chat.id, result)
    show_menu(call.message)


@bot.callback_query_handler(func=lambda call: call.data == 'plant_crop')
def plant_crop(call):
    bot.send_photo(call.message.chat.id, 'https://img.freepik.com/free-vector/watercolor-farmer-s-day-celebration-illustration_23-2149853553.jpg?t=st=1731267528~exp=1731271128~hmac=ef304ce45c9edfa9c0f2b391734809cf41172a42ab2b31696ff177aa27ac377d&w=740')
    user = get_or_create_user(call.from_user.id)
    if user.fields == 0:
        bot.send_message(call.message.chat.id, "У вас немає полів! Спочатку купіть поле.")
        show_menu(call.message)
        return
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton('Посіяти пшеницю', callback_data='plant_wheat'),
        types.InlineKeyboardButton('Посіяти рис', callback_data='plant_rice'),
        types.InlineKeyboardButton('Посіяти соняшник', callback_data='plant_sunflower')
    )
    bot.send_message(call.message.chat.id, "Оберіть культуру для посіву:", reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data == 'plant_wheat')
def plant_wheat(call):
    user = get_or_create_user(call.from_user.id)

    if user.fields == 0:
        bot.send_message(call.message.chat.id, "У вас немає полів! Спочатку купіть поле.")
        show_menu(call.message)
        return

    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(*[types.InlineKeyboardButton(f"Поле {i}", callback_data=f"select_field_wheat_{i}") for i in
                 range(1, user.fields + 1)])
    bot.send_message(call.message.chat.id, "Оберіть поле для посіву пшениці:", reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data.startswith('select_field_wheat_'))
def select_field_wheat(call):
    user = get_or_create_user(call.from_user.id)
    field = int(call.data.split('_')[-1])

    if field > user.fields or field <= 0:
        bot.send_message(call.message.chat.id, "Це поле не існує!")
        show_menu(call.message)
        return

    result = user.plant_crop(field, 'пшениця')
    bot.send_message(call.message.chat.id, result)
    show_menu(call.message)


@bot.callback_query_handler(func=lambda call: call.data == 'plant_rice')
def plant_rice(call):
    user = get_or_create_user(call.from_user.id)

    if user.fields == 0:
        bot.send_message(call.message.chat.id, "У вас немає полів! Спочатку купіть поле.")
        show_menu(call.message)
        return

    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(*[types.InlineKeyboardButton(f"Поле {i}", callback_data=f"select_field_rice_{i}") for i in
                 range(1, user.fields + 1)])
    bot.send_message(call.message.chat.id, "Оберіть поле для посіву рису:", reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data.startswith('select_field_rice_'))
def select_field_rice(call):
    user = get_or_create_user(call.from_user.id)
    field = int(call.data.split('_')[-1])

    if field > user.fields or field <= 0:
        bot.send_message(call.message.chat.id, "Це поле не існує!")
        show_menu(call.message)
        return

    result = user.plant_crop(field, 'рис')
    bot.send_message(call.message.chat.id, result)
    show_menu(call.message)


@bot.callback_query_handler(func=lambda call: call.data == 'plant_sunflower')
def plant_sunflower(call):
    user = get_or_create_user(call.from_user.id)

    if user.fields == 0:
        bot.send_message(call.message.chat.id, "У вас немає полів! Спочатку купіть поле.")
        show_menu(call.message)
        return

    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(*[types.InlineKeyboardButton(f"Поле {i}", callback_data=f"select_field_sunflower_{i}") for i in
                 range(1, user.fields + 1)])
    bot.send_message(call.message.chat.id, "Оберіть поле для посіву соняшнику:", reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data.startswith('select_field_sunflower_'))
def select_field_sunflower(call):
    user = get_or_create_user(call.from_user.id)
    field = int(call.data.split('_')[-1])

    if field > user.fields or field <= 0:
        bot.send_message(call.message.chat.id, "Це поле не існує!")
        show_menu(call.message)
        return

    result = user.plant_crop(field, 'соняшник')
    bot.send_message(call.message.chat.id, result)
    show_menu(call.message)


def process_plant_crop(message, crop):
    user = get_or_create_user(message.from_user.id)
    field = int(message.text)
    result = user.plant_crop(field, crop)
    bot.send_message(message.chat.id, result)
    show_menu(message)


@bot.callback_query_handler(func=lambda call: call.data == 'buy_seeds')
def buy_seeds(call):
    bot.send_photo(call.message.chat.id, "https://img.freepik.com/free-vector/outdoor-farm-market-stalls-wooden-fair-booths-kiosks-with-striped-awning-farmer-food-honey-dairy-products-vegetables-wood-vendor-counters-street-trading-cartoon-vector-illustration_107791-10531.jpg?t=st=1731268089~exp=1731271689~hmac=6ab80b18eca022461a67269013de30bd4647726d11e09130f212b6eb64ba6033&w=1380")
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton('Купити насіння пшениці (2 монети)', callback_data='buy_wheat_seed'),
        types.InlineKeyboardButton('Купити насіння рису (3 монети)', callback_data='buy_rice_seed'),
        types.InlineKeyboardButton('Купити насіння соняшнику (4 монети)', callback_data='buy_sunflower_seed')
    )
    bot.send_message(call.message.chat.id, "Оберіть насіння для покупки:", reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data == 'buy_stall')
def buy_stall(call):
    bot.send_photo(call.message.chat.id, "https://img.freepik.com/free-vector/outdoor-farm-market-stalls-wooden-fair-booths-kiosks-with-striped-awning-farmer-food-honey-dairy-products-vegetables-wood-vendor-counters-street-trading-cartoon-vector-illustration_107791-10531.jpg?t=st=1731268089~exp=1731271689~hmac=6ab80b18eca022461a67269013de30bd4647726d11e09130f212b6eb64ba6033&w=1380")
    user = get_or_create_user(call.from_user.id)
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton('Купити курник', callback_data='buy_chicken_stall'),
        types.InlineKeyboardButton('Купити корівник', callback_data='buy_cow_stall')
    )
    bot.send_message(call.message.chat.id, "Оберіть тварину для покупки загону:", reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data == 'buy_chicken_stall')
def buy_chicken_stall(call):
    user = get_or_create_user(call.from_user.id)
    result = user.buy_stall('курка')
    bot.send_message(call.message.chat.id, result)
    show_menu(call.message)


@bot.callback_query_handler(func=lambda call: call.data == 'buy_cow_stall')
def buy_cow_stall(call):
    user = get_or_create_user(call.from_user.id)
    result = user.buy_stall('корова')
    bot.send_message(call.message.chat.id, result)
    show_menu(call.message)


@bot.callback_query_handler(func=lambda call: call.data == 'expand_stall')
def expand_stall(call):
    user = get_or_create_user(call.from_user.id)
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton('Розширити курник', callback_data='expand_chicken_stall'),
        types.InlineKeyboardButton('Розширити корівник', callback_data='expand_cow_stall')
    )
    bot.send_message(call.message.chat.id, "Оберіть тварину для розширення загону:", reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data == 'expand_chicken_stall')
def expand_chicken_stall(call):
    user = get_or_create_user(call.from_user.id)
    result = user.expand_stall('курка')
    bot.send_message(call.message.chat.id, result)
    show_menu(call.message)


@bot.callback_query_handler(func=lambda call: call.data == 'expand_cow_stall')
def expand_cow_stall(call):
    user = get_or_create_user(call.from_user.id)
    result = user.expand_stall('корова')
    bot.send_message(call.message.chat.id, result)
    show_menu(call.message)


@bot.callback_query_handler(func=lambda call: call.data == 'buy_wheat_seed')
def buy_wheat_seed(call):
    user = get_or_create_user(call.from_user.id)
    if user.coins >= 2:
        user.coins -= 2
        user.resources['насіння_пшениці'] += 1
        bot.send_message(call.message.chat.id, "Ви купили насіння пшениці!")
    else:
        bot.send_message(call.message.chat.id, "Не вистачає монет для покупки насіння пшениці!")
    show_menu(call.message)


@bot.callback_query_handler(func=lambda call: call.data == 'buy_rice_seed')
def buy_rice_seed(call):
    user = get_or_create_user(call.from_user.id)
    if user.coins >= 3:
        user.coins -= 3
        user.resources['насіння_рису'] += 1
        bot.send_message(call.message.chat.id, "Ви купили насіння рису!")
    else:
        bot.send_message(call.message.chat.id, "Не вистачає монет для покупки насіння рису!")
    show_menu(call.message)


@bot.callback_query_handler(func=lambda call: call.data == 'buy_sunflower_seed')
def buy_sunflower_seed(call):
    user = get_or_create_user(call.from_user.id)
    if user.coins >= 4:
        user.coins -= 4
        user.resources['насіння_соняшнику'] += 1
        bot.send_message(call.message.chat.id, "Ви купили насіння соняшнику!")
    else:
        bot.send_message(call.message.chat.id, "Не вистачає монет для покупки насіння соняшнику!")
    show_menu(call.message)


def simulate_crop_growth(user, crop_type, field):
    if crop_type in user.field_crops and user.field_crops[field] == crop_type:
        city = user.city or "Kyiv"
        weather_data = get_weather(city)
        if weather_data is None:
            bot.send_message(user.user_id, "Не вдалося отримати інформацію про погоду.")
            return
        temp = weather_data['current']['temp_c']
        precipitation = weather_data['current']['precip_mm']
        growth_factor = 1
        if precipitation > 5:
            growth_factor = 1.5
        elif temp > 30:
            growth_factor = 0.5
        time.sleep(3600)
        if field in user.field_crops and user.field_crops[field] == crop_type:
            harvested_amount = random.randint(1, 3) * growth_factor
            user.resources[crop_type] += int(harvested_amount)
            bot.send_message(user.user_id, f"Ви зібрали {int(harvested_amount)} {crop_type} на полі {field}.")


def simulate_animal_production(user, animal_type):
    while True:
        time.sleep(3600)
        if animal_type == 'курка':
            harvested_eggs = random.randint(1, user.animals['курка'] * 2)
            user.resources['яйця'] += harvested_eggs
            bot.send_message(user.user_id, f"Ви зібрали {harvested_eggs} яєць від курок.")
        elif animal_type == 'корова':
            harvested_milk = random.randint(1, user.animals['корова'] * 2)
            user.resources['молоко'] += harvested_milk
            bot.send_message(user.user_id, f"Ви зібрали {harvested_milk} молока від корів.")


def crop_thread(message, crop):
    user = get_or_create_user(message.from_user.id)
    field = int(message.text)
    result = user.plant_crop(field, crop)
    bot.send_message(message.chat.id, result)
    if result.startswith("Ви посіяли"):
        threading.Thread(target=simulate_crop_growth, args=(user, crop, field)).start()
    show_menu(message)


bot.infinity_polling()
