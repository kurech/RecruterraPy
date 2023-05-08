from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import pyodbc
import hashlib
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
import nltk

API_TOKEN = '6218949302:AAFqBOsQE76s7j3eVVlNLcaRezSVQeU7uhU'

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

isauthorization = False
login_main = "admin@admin.ru"
isloginaccept = False
password_main = "password"

cnxn = pyodbc.connect("Driver={SQL Server Native Client 11.0};"
                      "Server=RANELPC;"
                      "Database=recruterra;"
                      "Trusted_Connection=yes;")

cursor = cnxn.cursor()


@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    await message.reply("Привет!\n\nАвторизуйтесь пожалуйста в системе:\n\n/login [ваш логин] - для ввода логина\n/password [ваш пароль] - для ввода пароля")


@dp.message_handler(commands=("login"), commands_prefix="/")
async def send_enter_login(message: types.Message):
    global login_main
    value = message.text
    value = value[7:]
    login_main = value
    await message.answer("Ваш логин записан! Используйте /password [ваш пароль] для ввода пароля")


@dp.message_handler(commands=("password"), commands_prefix="/")
async def send_enter_password(message: types.Message):
    value = message.text
    value = value[10:]
    cursor.execute('SELECT Id, Login, Password FROM Users')
    users = cursor.fetchall()

    for user in users:
        if (user.Login == login_main) and (user.Password == password_hashing(value)):
            cursor.execute(
                'INSERT INTO Administrator (Id, TelegramId) VALUES (?, ?)', (user.Id, message.from_user.id))
            cnxn.commit()
            await message.answer("Вы успешно вошли в аккаунт!")


@dp.message_handler(commands=['profile'])
async def send_profile(message: types.Message):
    for adm in cursor.execute('SELECT Id, TelegramId FROM Administrator'):
        if adm.TelegramId == message.from_user.id:
            await message.answer(f"Вы авторизованы под аккаунтом: {find_user_by_id(adm.Id)}!")
        else:
            await message.answer("Вы не авторизованы!")


@dp.message_handler(commands=['vacancies'])
async def send_vacancies(message: types.Message):
    cursor.execute(
        'SELECT Id, Position, Obligations, Salary, IsActive FROM Vacancies')
    vacancies = cursor.fetchall()
    for vacancy in vacancies:
        if vacancy.IsActive == 0:
            await message.answer(f"Вакансия: {vacancy.Position}\n{vacancy.Obligations}\n{vacancy.Salary} руб.")


@dp.message_handler(commands=['realfake'])
async def send_algorithm(message: types.Message):
    cursor.execute(
        'SELECT * FROM Vacancies')
    vacancies = cursor.fetchall()
    for vacancy in vacancies:
        if vacancy.IsActive == 0:
            fake_job = {'Title': str(vacancy.Position),
                        'Salary': str(vacancy.Salary),
                        'Description': str(vacancy.Description),
                        'Requirements': str(vacancy.Obligations),
                        'Conditions': str(find_typeemp_by_id(vacancy.IdTypeOfEmployment)),
                        'WorkEx': str(vacancy.WorkExperience),
                        'Exist': False}
            vacancyacceptkb = InlineKeyboardMarkup(row_width=2)
            vacancyacceptbutton = InlineKeyboardButton(
                text='Принять', callback_data=f'accept_{vacancy.Id}')
            vacancydissmisbutton = InlineKeyboardButton(
                text='Отклонить', callback_data=f'dismiss_{vacancy.Id}')
            vacancyacceptkb.add(vacancyacceptbutton, vacancydissmisbutton)
            await message.answer(f"Вакансия: {vacancy.Position}\n{vacancy.Obligations}\n{vacancy.Salary} руб.\n\nАлгоритм, который использует метод случайного леса предполагает, что {jobRandomForestClassifier(fake_job)}\n\nАлгоритм, который использует метод логической регрессии предполагает, что {jobLogisticRegression(fake_job)}", reply_markup=vacancyacceptkb)


def find_user_by_id(id):
    for adm in cursor.execute('SELECT Id, Login FROM Users'):
        if adm.Id == id:
            return adm.Login


def find_typeemp_by_id(id):
    for typeemp in cursor.execute('SELECT Id, Type FROM TypeOfEmployments'):
        if typeemp.Id == id:
            return typeemp.Type


def get_vacancy_by_id(id):
    cursor.execute(
        f'SELECT * FROM Vacancies WHERE Id = {id}')
    vacancies = cursor.fetchall()
    for vacancy in vacancies:
        return vacancy.Position


def password_hashing(s):
    hash_object = hashlib.sha1(s.encode())
    hex_dig = hash_object.hexdigest()
    return hex_dig


@dp.callback_query_handler(lambda c: c.data and c.data.startswith(('accept_', 'dismiss_')))
async def handle_callback_query(callback_query: types.CallbackQuery):
    command, vacancy_id = callback_query.data.split('_')
    vacancy = get_vacancy_by_id(vacancy_id)
    if command == 'accept':
        await bot.answer_callback_query(
            callback_query.id,
            text=f"Вакансия {vacancy} была принята", show_alert=True)
        cursor.execute(
            f'UPDATE Vacancies SET IsActive=1 WHERE Id={vacancy_id}')
        cnxn.commit()
        await bot.edit_message_reply_markup(
            chat_id=callback_query.from_user.id,
            message_id=callback_query.message.message_id,
            reply_markup=None
        )
    elif command == 'dismiss':
        await bot.answer_callback_query(
            callback_query.id,
            text=f"Вакансия {vacancy} была отклонена", show_alert=True)
        cursor.execute(
            f'UPDATE Vacancies SET IsActive=2 WHERE Id={vacancy_id}')
        cnxn.commit()
        await bot.edit_message_reply_markup(
            chat_id=callback_query.from_user.id,
            message_id=callback_query.message.message_id,
            reply_markup=None
        )


@dp.message_handler()
async def echo(message: types.Message):
    await message.answer("Выберите действие: ")


def jobLogisticRegression(fake_job):
    # Загрузка данных
    data = pd.read_csv('dataset.csv', sep=';', header=None)
    data.columns = ['Title', 'Salary', 'Description',
                    'Requirements', 'Conditions', 'WorkEx', 'Exist']

    # Добавление фейковой вакансии в данные
    data = data._append(fake_job, ignore_index=True)

    # Создание корпуса текстов
    corpus = data['Title'] + ' ' + data['Salary'] + ' ' + data['Description'] + \
        ' ' + data['Requirements'] + ' ' + \
        data['Conditions'] + ' ' + data['WorkEx']

    # Создание матрицы TF-IDF признаков
    vectorizer = TfidfVectorizer()
    X = vectorizer.fit_transform(corpus)

    # Обучение модели логистической регрессии
    y = data['Exist']
    clf = LogisticRegression()
    clf.fit(X[:-1], y[:-1])

    # Предсказание результата для новой вакансии
    fake_job_vector = vectorizer.transform(
        [fake_job['Title'] + ' ' + fake_job['Salary'] + fake_job['Description'] + ' ' + fake_job['Requirements'] + ' ' + fake_job['Conditions'] + ' ' + fake_job['WorkEx']])
    fake_job_prob = clf.predict_proba(fake_job_vector)[0][1]

    # Вывод результата
    if fake_job_prob > 0.2:
        result = f'вакансия является ненастоящей ({round((1 - fake_job_prob) * 100, 3)}%)'
        return result
    else:
        result = f'вакансия является настоящей ({round((1 - fake_job_prob) * 100, 3)}%)'
        return result


def jobRandomForestClassifier(fake_job):
    data = pd.read_csv('dataset.csv', sep=';', header=None)
    data.columns = ['Title', 'Salary', 'Description',
                    'Requirements', 'Conditions', 'WorkEx', 'Exist']

    data = data._append(fake_job, ignore_index=True)
    corpus = data['Title'] + ' ' + data['Salary'] + ' ' + data['Description'] + \
        ' ' + data['Requirements'] + ' ' + \
        data['Conditions'] + ' ' + data['WorkEx']
    stop_words = nltk.corpus.stopwords.words('russian')
    vectorizer = TfidfVectorizer(stop_words=stop_words)
    X = vectorizer.fit_transform(corpus)
    y = data['Exist']
    clf = RandomForestClassifier()
    clf.fit(X[:-1], y[:-1])
    fake_job_vector = vectorizer.transform([fake_job['Title'] + ' ' + fake_job['Salary'] + fake_job['Description'] +
                                           ' ' + fake_job['Requirements'] + ' ' + fake_job['Conditions'] + ' ' + fake_job['WorkEx']])
    fake_job_prob = clf.predict_proba(fake_job_vector)[0][1]
    if fake_job_prob > 0.2:
        result = f'вакансия является ненастоящей ({round((1 - fake_job_prob) * 100, 3)}%)'
        return result
    else:
        result = f'вакансия является настоящей ({round((1 - fake_job_prob) * 100, 3)}%)'
        return result


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
