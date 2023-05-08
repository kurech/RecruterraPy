import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import RandomForestClassifier
import nltk

# Загрузка данных
data = pd.read_csv('dataset.csv', sep=';', header=None)
data.columns = ['Title', 'Salary', 'Description',
                'Requirements', 'Conditions', 'WorkEx', 'Exist']


fake_job = {'Title': 'вапвапва',
            'Salary': '55000',
            'Description': 'вапварукр',
            'Requirements': 'лорывадылпваыва',
            'Conditions': 'Полная занятость',
            'WorkEx': 'Без опыта',
            'Exist': False}

# Добавление фейковой вакансии в данные
data = data._append(fake_job, ignore_index=True)

# Создание корпуса текстов
corpus = data['Title'] + ' ' + data['Salary'] + ' ' + data['Description'] + \
    ' ' + data['Requirements'] + ' ' + \
    data['Conditions'] + ' ' + data['WorkEx']

# Удаление стоп-слов
stop_words = nltk.corpus.stopwords.words('russian')

# Создание матрицы TF-IDF признаков
vectorizer = TfidfVectorizer(stop_words=stop_words)
X = vectorizer.fit_transform(corpus)

# Обучение модели случайного леса
y = data['Exist']
clf = RandomForestClassifier()
clf.fit(X[:-1], y[:-1])

# Предсказание результата для новой вакансии
fake_job_vector = vectorizer.transform(
    [fake_job['Title'] + ' ' + fake_job['Salary'] + fake_job['Description'] + ' ' + fake_job['Requirements'] + ' ' + fake_job['Conditions'] + ' ' + fake_job['WorkEx']])
fake_job_prob = clf.predict_proba(fake_job_vector)[0][1]

# Вывод результата
if fake_job_prob > 0.2:
    result = f'Данная вакансия является ненастоящей.\nВероятность: {round((1 - fake_job_prob) * 100, 3)}%'
    print(result)
else:
    result = f'Данная вакансия является настоящей.\nВероятность: {round((1 - fake_job_prob) * 100, 3)}%'
    print(result)
