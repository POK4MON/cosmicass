import re
from datetime import datetime
import pyttsx3
import speech_recognition as sr
from vosk import Model, KaldiRecognizer
import json
import os
import pyaudio
import time

# Инициализация text-to-speech
tts_engine = pyttsx3.init()
tts_engine.setProperty('rate', 150)
tts_engine.setProperty('volume', 0.9)

# Настройка русского голоса
voices = tts_engine.getProperty('voices')
russian_voice = next((voice.id for voice in voices if 'russian' in voice.name.lower() or 'ru' in voice.id.lower()), None)
if russian_voice:
    tts_engine.setProperty('voice', russian_voice)
else:
    print("Внимание: Русский голос не найден, используется голос по умолчанию.")

# Инициализация Vosk
model_path = r"vosk-model-ru-0.22"  # Укажите путь к вашей модели Vosk
if not os.path.exists(model_path):
    print(f"Ошибка: Модель Vosk не найдена по пути {model_path}. Убедитесь, что модель установлена.")
    exit(1)
model = Model(model_path)
recognizer = KaldiRecognizer(model, 16000)

# Инициализация микрофона
mic = sr.Microphone()

# Структура расписания
schedule = []

# Члены экипажа
crew_members = ['капитан экипажа', 'борт инженер 4', 'борт инженер 5', 'борт инженер 6', 'борт инженер 11', 'борт инженер 13', 'борт инженер 18']

# Словарь для преобразования словесных чисел в цифры
number_map = {
    'ноль': '0', 'один': '1', 'два': '2', 'три': '3', 'четыре': '4',
    'пять': '5', 'шесть': '6', 'семь': '7', 'восемь': '8', 'девять': '9',
    'десять': '10', 'одиннадцать': '11', 'двенадцать': '12', 'тринадцать': '13',
    'четырнадцать': '14', 'пятнадцать': '15', 'шестнадцать': '16',
    'семнадцать': '17', 'восемнадцать': '18', 'девятнадцать': '19',
    'двадцать': '20', 'тридцать': '30', 'сорок': '40', 'пятьдесят': '50'
}

# Преобразование словесных чисел в цифры
def words_to_number(text):
    words = text.split()
    result = []
    i = 0
    while i < len(words):
        word = words[i].lower()
        if word in number_map:
            if word in ['двадцать', 'тридцать', 'сорок', 'пятьдесят']:
                if i + 1 < len(words) and words[i + 1].lower() in number_map:
                    result.append(str(int(number_map[word]) + int(number_map[words[i + 1].lower()])))
                    i += 2
                else:
                    result.append(number_map[word])
                    i += 1
            else:
                result.append(number_map[word])
                i += 1
        else:
            result.append(word)
            i += 1
    return ' '.join(result)

# Парсинг расписания
def parse_schedule():
    ocr_data = [
        # Страница 1
        """
        06:00-06:35 | капитан экипажа | Утренний туалет
        06:00-06:10 | борт инженер 4 | Осмотр станции <br> Тестирование ПСС / РСУ п. 4.3 cmp. 4-2 (45)
        06:00-06:10 | борт инженер 5 | Осмотр станции <br> Перезагрузка Laptop RS1 / БВС п.2.1.2.1 cmp.2-3 (14) <br> Перезагрузка RSS1 / p/2 1385
        06:00-06:45 | борт инженер 6 | Утренний туалет
        06:00-06:05 | борт инженер 11 | Чтение напоминания
        06:00-06:10 | борт инженер 13 | Осмотр станции <br> Перезагрузка Laptop RS4, RS MLM / БВС п. 2.1.2.1 cmp.2-3 (14)
        06:00-06:55 | борт инженер 18 | Утренний туалет
        06:05-06:50 | борт инженер 11 | Утренний туалет
        06:10-06:30 | борт инженер 4 | Утренний туалет
        06:10-06:40 | борт инженер 5 | Утренний туалет
        06:10-06:25 | борт инженер 13 | МО-8. Сборка схемы / МО кн. 2 п. 10.1 cmp.10-1 по 10-6 (156-161)
        06:25-06:30 | борт инженер 13 | МО-8. Измерение массы тела / МО кн. 2 п. 10.2 cmp.10-7 (162)
        06:30-06:35 | борт инженер 4 | МО-8. Измерение массы тела / МО кн. 2 п. 10.2 cmp.10-7 (162)
        06:30-07:05 | борт инженер 13 | Завтрак
        06:35-06:40 | капитан экипажа | МО-8. Измерение массы тела / МО кн. 2 п. 10.2 cmp.10-7 (162)
        06:35-07:30 | борт инженер 4 | Завтрак
        06:40-07:30 | капитан экипажа | Утренний туалет
        06:40-06:45 | борт инженер 5 | МО-8. Измерение массы тела / МО кн. 2 п. 10.2 cmp.10-7 (162)
        06:45-07:30 | борт инженер 5 | Завтрак
        06:45-06:50 | борт инженер 6 | МО-8. Измерение массы тела / МО кн. 2 п. 10.2 cmp.10-7 (162)
        06:50-07:30 | борт инженер 6 | Утренний туалет
        06:50-06:55 | борт инженер 11 | МО-8. Измерение массы тела / МО кн. 2 п. 10.2 cmp.10-7 (162)
        06:55-07:25 | борт инженер 11 | Утренний туалет
        06:55-07:00 | борт инженер 18 | МО-8. Измерение массы тела / МО кн. 2 п. 10.2 cmp.10-7 (162)
        07:00-07:30 | борт инженер 18 | Утренний туалет
        07:05-07:20 | борт инженер 13 | МО-8. Заключительные операции / МО кн. 2 п. 10.3 .1 cmp. $10-8$ (163)
        07:20-07:30 | борт инженер 13 | МО-8. Передача данных на Землю после измерения массы тела / МО кн. 2 п. 10.3 .2 cmp. $10-9$ (164)
        07:25-07:30 | борт инженер 11 | ВIOM. Нанесение смазки на электроды монитора ЭКГ
        07:30-07:45 |  | Ежедневная конференция по планированию (S-band)
        07:45-08:15 | капитан экипажа, борт инженер 11, борт инженер 18 | Подготовка к работе
        07:45-08:10 | борт инженер 4 | Подготовка к работе
        """,
        # Страница 2
        """
        07:45-07:55 | борт инженер 5 | ВЗАИМОДЕЙСТВИЕ-2. Заключительные операции. Установка «Актиграфа» на заряд / p/z 3137
        07:45-07:50 | борт инженер 6 | Установка на заряд батареек для фото- и видеотехники
        07:45-07:55 | борт инженер 13 | ВЗАИМОДЕЙСТВИЕ-2. Заключительные операции. Установка «Актиграфа» на заряд / p/z 3138
        07:50-08:00 | борт инженер 6 | Замена ЕДВ в системе перекачки урины UTS
        08:00-08:20 | борт инженер 6 | Проверка датчиков воздушного потока WIS RSU A1 в модуле JEM
        """
    ]

    time_pattern = r'(\d{2}:\d{2}-\d{2}:\d{2}|\d{2}:\d{2})\s*\|\s*([^|]*?)\s*\|\s*(.*?)(?=\n|$|\d{2}:\d{2})'
    for page in ocr_data:
        matches = re.finditer(time_pattern, page, re.DOTALL)
        for match in matches:
            time_slot = match.group(1).strip()
            crew = match.group(2).strip()
            task = match.group(3).strip().replace('<br>', '; ').replace('\n', '; ')
            task = re.sub(r'\s*;\s*', '; ', task).strip('; ')
            crew_list = [c.strip() for c in crew.split(',')] if crew else ['Все']
            schedule.append({'time': time_slot, 'crew': crew_list, 'task': task})

# Парсинг времени
def parse_time(time_str):
    if '-' in time_str:
        return datetime.strptime(time_str.split('-')[0], '%H:%M')
    return datetime.strptime(time_str, '%H:%M')

# Получение задач по члену экипажа
def get_tasks_by_crew(crew_id):
    return sorted([entry for entry in schedule if crew_id in entry['crew']], key=lambda x: parse_time(x['time']))

# Получение задач по времени
def get_tasks_at_time(time_str):
    try:
        input_time = datetime.strptime(time_str, '%H:%M')
        tasks = []
        for entry in schedule:
            if '-' in entry['time']:
                start_str, end_str = entry['time'].split('-')
                start_time = datetime.strptime(start_str, '%H:%M')
                end_time = datetime.strptime(end_str, '%H:%M')
                if start_time <= input_time <= end_time:
                    tasks.append(entry)
            else:
                task_time = datetime.strptime(entry['time'], '%H:%M')
                if task_time == input_time:
                    tasks.append(entry)
        return tasks
    except ValueError:
        return []

# Получение списка членов экипажа
def get_crew_members():
    return crew_members

# Голосовой вывод
def speak(text):
    print(text)
    tts_engine.say(text)
    tts_engine.runAndWait()

# Голосовой ввод
def listen():
    p = pyaudio.PyAudio()
    stream = p.open(format=pyaudio.paInt16, channels=1, rate=16000, input=True, frames_per_buffer=1024)
    speak("Говорите команду.")

    frames = []
    timeout = time.time() + 5  # Ожидание 5 секунд
    while time.time() < timeout:
        data = stream.read(1024, exception_on_overflow=False)
        frames.append(data)
        if recognizer.AcceptWaveform(data):
            result = recognizer.Result()
            result_dict = json.loads(result)
            command = result_dict.get('text', '').lower()
            if command:
                print(f"Распознана команда: {command}")
                stream.stop_stream()
                stream.close()
                p.terminate()
                # Преобразуем словесные числа в цифры
                command = words_to_number(command)
                return command

    stream.stop_stream()
    stream.close()
    p.terminate()
    speak("Команда не распознана. Попробуйте снова или введите текстом.")
    return input("Введите команду: ").lower()

# Форматирование задач
def format_tasks(tasks):
    if not tasks:
        return "Нет задач для указанного запроса."
    output = []
    for task in tasks:
        output.extend([f"Время: {task['time']}", f"Экипаж: {', '.join(task['crew'])}", f"Задача: {task['task']}", "-" * 50])
    return "\n".join(output)

# Основной цикл
def main():
    parse_schedule()
    welcome = "Локальный ассистент космонавта для расписания на 10 января 2025 года. Скажите: 'список экипажа', 'задачи для' и имя, например, 'капитан экипажа' или 'борт инженер четыре', 'задачи на' и время, например, 'восемь ноль ноль', или 'выход'."
    speak(welcome)

    while True:
        command = listen()
        if 'список экипажа' in command:
            crew_list = ', '.join(get_crew_members())
            speak(f"Члены экипажа: {crew_list}")
        elif 'задачи для' in command or 'задача для' in command:
            # Преобразуем команду для поиска позывного с числом
            command_normalized = words_to_number(command)
            for crew_id in crew_members:
                if crew_id.lower() in command_normalized:
                    tasks = get_tasks_by_crew(crew_id)
                    speak(f"Задачи для {crew_id}:")
                    speak(format_tasks(tasks))
                    break
            else:
                speak("Неверный идентификатор члена экипажа. Назови, например, 'капитан экипажа' или 'борт инженер четыре'.")
        elif 'задачи на' in command or 'задача на' in command:
            time_sheld = command[9:]  # Извлекаем часть команды после "задачи на"
            # Преобразуем словесное время в числовое
            time_sheld_normalized = words_to_number(time_sheld)
            time_patterns = [r'(\d{1,2})\s*ноль\s*ноль', r'(\d{1,2})\s*час', r'(\d{1,2})\s*(\d{2})']
            time_str = None
            for pattern in time_patterns:
                match = re.search(pattern, time_sheld_normalized)
                if match:
                    groups = match.groups()
                    if len(groups) == 1:
                        time_str = f"{groups[0].zfill(2)}:00"
                    else:
                        time_str = f"{groups[0].zfill(2)}:{groups[1]}"
                    break
            if time_str:
                speak(f"Задачи на {time_str}:")
                tasks = get_tasks_at_time(time_str)
                speak(format_tasks(tasks))
            else:
                speak("Неверный формат времени. Назови время, например, 'восемь ноль ноль' или 'восемь тридцать'.")
        elif 'выход' in command:
            speak("Выход из программы.")
            break
        else:
            speak("Команда не распознана. Скажите: 'список экипажа', 'задачи для', 'задачи на' или 'выход'.")

if __name__ == "__main__":
    main()