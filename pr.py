import requests
from bs4 import BeautifulSoup
from telegram.ext import*
import sqlite3
import time


TOKEN = "7211036278:AAHoDDlP14l88jYLFVEmu2YShtNd0yw3UZE"
database = sqlite3.connect('my_db.db')
cursor = database.cursor() # объект "курсор" для выполнения SQL-запросов и операций с базой данных


cursor.execute('''
CREATE TABLE IF NOT EXISTS parsing_data (
id INTEGER PRIMARY KEY,
title TEXT NOT NULL,
company TEXT NOT NULL,
city TEXT NOT NULL,
experience TEXT NOT NULL,
salary TEXT NOT NULL,
link TEXT NOT NULL
)
''')
database.commit()

filter_translator=[['высшее','higher'],['Не требуется или не указано','not_required_or_not_specified'],['Среднее профессиональное','special_secondary'],['Не имеет значения',''],['От 1 года до 3 лет','between1And3'],['Нет опыта','noExperience'],['От 3 до 6 лет','between3And6'],['Более 6 лет','moreThan6']]







# Функция для получения списка вакансий с HH.ru
def get_vacancies(keywords, page=1,salary_fl='',education_fl='',experience_fl=''):
    url = f"https://hh.ru/search/vacancy?text={keywords}&page={page}&salary={salary_fl}&education={education_fl}&experience={experience_fl}"
    headers = {
        "User-Agent": "Chrome/78.0.3904.87 "
    }
    response = requests.get(url,timeout=30,headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')
    vacancy_items = soup.find_all('div', {'class': 'vacancy-search-item__card serp-item_link vacancy-card-container--OwxCdOj5QlSlCBZvSggS'})
    vacancies = []



    for item in vacancy_items:

        title = item.find('span', {'class': 'vacancy-name--c1Lay3KouCl7XasYakLk serp-item__title-link'}).text.strip()
        try:
            company = item.find('span', {'class': 'company-info-text--vgvZouLtf8jwBmaD1xgp'}).text.strip()
        except:
            continue
        city = item.find('span',{'data-qa' : 'vacancy-serp__vacancy-address'}).text
        experience=item.find('span',{'class':'label--rWRLMsbliNlu_OMkM_D3 label_light-gray--naceJW1Byb6XTGCkZtUM'}).text.strip()
        salary1 = None
        salary = item.find('span', {
            'class': 'fake-magritte-primary-text--Hdw8FvkOzzOcoR4xXWni compensation-text--kTJ0_rp54B2vNeZ3CTt2 separate-line-on-xs--mtby5gO4J0ixtqzW38wh'})
        if salary is None:
            salary1 = 'нет данных'
        else:
            salary1 = salary.text
        link = item.find('a', {'class': 'bloko-link'})['href']
        cursor.execute('''
        INSERT OR IGNORE INTO parsing_data VALUES(NULL,?,?,?,?,?,?)''',(title,company,city,experience,salary1,link))
        database.commit()


        vacancy = {
            'title': title,
            'company':company ,
            'city' : city,
            'experience': experience,
            'salary' : salary1,
            'link': link,
        }
        vacancies.append(vacancy)

    return vacancies




# Функция для отправки списка вакансий в чат
async def send_vacancies(update, context):
    cursor.execute('''DELETE FROM parsing_data''')
    keywords = update.message.text.strip('/vacancies ')
    keywords=keywords.lower()

    if ',' in keywords: #проверка на наличие фильтра
        filter_array=list(map(str,keywords.split(', ')))
        Keyword=filter_array[0]
        filter_array.remove(Keyword)
        for n in range(len(filter_translator)):

            if filter_translator[n][0] in filter_array:
                filter_array[filter_array.index(filter_translator[n][0])]=filter_translator[n][1]

    else:
        filter_array = ['','','']

    for i in range(1): #кол-во страниц
        try:

            vacancies = get_vacancies(keywords,i,filter_array[0],filter_array[1],filter_array[2])
        except IndexError:
            await context.bot.send_message(chat_id=update.effective_chat.id,
                                           text="Некорректный ввод фильтра.")
            break
        cursor.execute('''SELECT COUNT(*) FROM parsing_data''')
        count=cursor.fetchone()
        await context.bot.send_message(chat_id=update.effective_chat.id,text=f"Найдено {count[0]} вакансий по заданному запросу.")
        time.sleep(3)
        if vacancies:
            #await context.bot.send_message(chat_id=update.effective_chat.id,text=f"Найдено {len(vacancies)} вакансий")
            for vacancy in vacancies:
               await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Вакансия: {vacancy['title']}\nКомпания: {vacancy['company']}\nГород: {vacancy['city']}\nОпыт работы:{vacancy['experience']}\nЗарплата:{vacancy['salary']}\nСсылка: {vacancy['link']}")
        else:
            await context.bot.send_message(chat_id=update.effective_chat.id, text="Не найдено вакансий по заданному запросу.")

# Функция для обработки команды /start,help

async def start(update, context):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Привет! Я бот для поиска вакансий на HH.ru. Введите команду /vacancies [вакансия] для поиска вакансий. Если хотите поиск вакансии с фильтрами, то введите '/vacancies [вакансия], [фильтр], [фильтр], [фильтр]'. Для ознакомления с фильтрами введите /help ")
async def get_help(update, context):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Типы фильтров:зарплата, образование, опыт работы(в строгом порядке)\nЗарплата:любое число\nОбразование:высшее, среднее профессиональное, не имеет значения\nОпыт работы:От 1 года до 3 лет, От 3 до 6 лет, Нет опыта\nПример:/vacancies врач, 40000, высшее, нет опыта\nЕсли определенный фильтр не нужен, то введите '-'\nПример:/vacancies врач, -, высшее, нет опыта")
# Настройка бота

application = Application.builder().token(TOKEN).build()

# Задание обработчиков команд
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("vacancies", send_vacancies))
application.add_handler(CommandHandler("help", get_help))
#database.close()



# Запуск бота
application.run_polling(1.0)
