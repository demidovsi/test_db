import json
import os
import time
import requests
from requests.exceptions import HTTPError

url = ''  # url для обращения к RestAPI
directories_files = []  # массив директорий, в которых могут находиться тестируемые файлы
config_name = ''  # имя загруженной конфигурации (это на будущее, пока берется нулевой элемент массива из config.json)
prefix = ''  # часть имени файлов, которые нужно удалять при формировании запроса (добавления к url)

st_error = 'Ошибка запроса к RestApi'
q_test, q_error, q_except, q_not_found, max_len_message, q_request = 0, 0, 0, 0, 0, 0
tek_proc, compare_wait_text_for_error = '', True
mas_error, mas_codes, mas_codes_text = [], {}, []


def load_config(name=None):
    """
    Чтение конфигурационных параметров для указанной конфигурации.
    Конфигурации находятся в файле config.json.
    При отсутствии в файле конфигурации с указанным именем читается нулевая конфигурация.
    :param name: имя требуемой конфигурации.
    :return: True, если все нормально и False, если ошибки или нет файла конфигураций или он пуст.
    Если отсутствует файл или при его чтении и разборе возникает ошибка, то выполнение программы завершается,
    текст ошибки распечатывается. То же самое, если файл имеется, но он пуст.
    """
    def read_config(config_json):
        # вытаскиваем из указанного json нужные параметры
        global url, directories_files, config_name, prefix  # ссылки на глобальные переменные
        url = config_json['url']
        directories_files = config_json['directories_files'].split(',')
        for i in range(len(directories_files)):
            directories_files[i] = directories_files[i].strip()
        config_name = config_json['name']
        prefix = config_json['prefix']
    # прочитать заданную конфигурацию
    try:
        f = open('config.json', 'r', encoding='utf-8')  # открываем файл в текущей директории
        with f:
            configs = json.loads(f.read())  # читаем содержимое файла и переводим в json формат
            for config in configs:
                if config['name'] == name:
                    read_config(config)  # этот элемент json и является заданным, читаем из него параметры
                    return True
        read_config(configs[0])  # заданное имя не найдено, читаем из нулевого (если он есть)
        return True
    except Exception as err:
        print('Fatal error:', 'load_config', 'name=', name, f"{err}")
        return False


def load_files(directory_file):
    """
    Создаем список файлов из указанной директории.
    :param directory_file: директория, в которой находятся тестируемые файлы.
    :return: массив имен файлов из указанной директории.
    """
    return os.listdir(directory_file)


def dop_st(st: str, n: int, sim: str = ' ', to_right=True) -> str:
    """
    Дополнение строки справа символом sim до длины в n знаков.
    Дополнение производится только, если входная строка имеет длину менее n знаков.
    Входные параметры:
        st - дополняемая строка
        n - требуемая длина строки
        sim - символ дополнения строки (по умолчанию - пробел)
        to_right - признак добавления справа
    возвращаемые данные:
        строка, дополненная указанным символов
    """
    while len(st) < n:
        if to_right:
            st += sim
        else:
            st = sim + st
    return st


def print_zag():
    """ Печать строк заголовка для лога тестирования """
    print(dop_st('', 205, '-'))
    st_tek_proc = dop_st('тип запроса', 16)
    st_test = 'тест  '
    st_directive = dop_st('дирек', 6)
    st_result = dop_st('result', 8)
    st_time = dop_st(dop_st('T', 3), 5, to_right=False)
    message = dop_st('команда', 40)
    reason = dop_st('статус команды', 32)
    st_answer = 'ответ,'
    st_params = 'параметры'
    print(' №№', ' ID  ', st_tek_proc, st_test, st_directive, 'токен', st_result, st_time, message, reason,
          st_answer, st_params, sep='|')
    print(dop_st('', 205, '-'), flush=True)


def clear_results():
    """
    Сброс характеристик предыдущего теста.
    :return:
    """
    global q_test, q_error, q_except, q_not_found, tek_proc, max_len_message, q_request, compare_wait_text_for_error
    global mas_error, mas_codes, mas_codes_text

    q_test, q_error, q_except, q_not_found, max_len_message, q_request = 0, 0, 0, 0, 0, 0
    tek_proc, compare_wait_text_for_error = '', True
    mas_error, mas_codes, mas_codes_text = [], {}, []


def ordered(obj):
    """
    Упорядочивание json (для сравнения)
    :param obj:
    :return:
    """
    if isinstance(obj, dict):
        return sorted((k, ordered(v)) for k, v in obj.items())
    if isinstance(obj, list):
        return sorted(ordered(x) for x in obj)
    else:
        return obj


def make_command(directive, message, wait_result, file_answer,
                 text_usl='', params='', token=None,
                 id_test=None, wait_text_for_error=None, show_params=True):
    """
    Выполнение запроса к Rest API и вывод результата в лог тестирования.
    :param directive:
    :param message:
    :param wait_result: ожидаемый результат запроса
    :param file_answer: имя файла с ожидаемым ответом на запрос
    :param text_usl:
    :param params:
    :param token:
    :param id_test:
    :param wait_text_for_error:
    :param show_params:
    :return:
    """
    global q_except
    global q_not_found
    global mas_codes, mas_codes_text
    if text_usl != '':
        message = message + '?usl=' + text_usl
    t_begin = time.time()
    if params == '':
        data, result, reason, status_code = send_rest(message, directive, token_user=token)
    else:
        data, result, reason, status_code = send_rest(message, directive, params=params, token_user=token)
    t_begin = time.time() - t_begin
    not_equal = False
    if result:  # запрос завершился удачно, будем проверять на совпадение ответа и содержимого файла
        try:
            f = open(file_answer, 'r', encoding='utf-8')  # открываем файл
            with f:
                data_json = json.loads(f.read())  # читаем содержимое файла и переводим в json формат
                result = ordered(data_json) == ordered(json.loads(data))
                if not result:
                    not_equal = True
        except Exception as err:
            print('Error:', 'make_command', 'file_answer=', file_answer, f"{err}")
            result = False

    val_status_code = mas_codes[str(status_code)] if str(status_code) in mas_codes else 0
    mas_codes[str(status_code)] = val_status_code + 1
    if reason not in mas_codes_text:
        mas_codes_text.append(reason)
    if status_code in [404, 405]:
        q_not_found += 1
        data = '??? ' + data
    elif status_code >= 500:
        q_except += 1
    if wait_text_for_error and not result and compare_wait_text_for_error:
        if wait_text_for_error not in data:
            wait_result = not result
    print_result(message, result, reason, data, params, wait_result, directive, token,
                 t_begin, id_test, show_params=show_params, not_equal=not_equal)
    return data, result


def send_rest(message, directive="GET", params=None, language='', token_user=None):
    """ Обращение к Rest API с переданным запросом
    входные параметры:
        message - текст команды (endpoint и параметры)
        directive - директива выполнения для Rest API
        params - возможные параметры для BODY в виде строки или словаря (dict)
        language - необязательный параметр: идентификатор языка для возврата возможных ошибок
        token_user - необязательный параметр: токен пользователя для команд, требующих токен с правами пользователя
    возвращаемые значения:
       - строка полученного ответа (или текст ошибки прерывания)
       - boolean результат обработки команды
       - текст с кодом статуса команды и его текстовая расшифровка
    """
    # формирование json для BODY
    global q_request
    js = {}
    if token_user is not None:
        js['token'] = token_user
    if language != '':
        js['lang'] = language  # код языка пользователя
    if params:
        if type(params) is not str:
            params = json.dumps(params, ensure_ascii=False)
        js['params'] = params  # дополнительно заданные параметры

    q_request += 1
    # выдача Rest запроса, используется глобальная константа url для идентификации сервера Rest
    try:
        headers = {"Accept": "application/json"}
        response = requests.request(directive, url + message, headers=headers, json=js)

    # обработка ошибок от HTTP
    except HTTPError as err:
        txt = f'  ===>  HTTP error occurred: {err}'
        return txt, False, st_error
    # обработка других ошибок
    except Exception as err:
        txt = f'  ===>  Other error occurred: {err}'
        return txt, False, st_error

    else:
        # передача ответа от Rest на переданный запрос
        return response.text, response.ok, '<' + str(response.status_code) + '> - ' + response.reason, \
               response.status_code


def boolean_str(val, true, false):
    """
    для boolean возвращается текст true или false для значения True и False
    :param val: - логическое значение
    :param true: - символьное изображение для значения True
    :param false: - символьное изображение для значения False
    :return: указанное символьное изображение логического значения указанными строками
    """
    if val:
        return true
    else:
        return false


def is_token(user_token):
    """ Возвращается строка с признаком наличия переданного параметра token:
    5 пробелов (если token отсутствует) или слово "токен" (если token задан)
    """
    if user_token is None:
        return '     '
    else:
        return 'Token'


def print_result(message, result, reason, data, params, wait_result, directive, user_token,
                 time_operation=None, id_test=None, show_params=True, not_equal=False):
    """
    Печать (в одну строку) результатов тестирования
    Одновременно производится подсчет количества тестов и количество не пройденных тестов
    :param message:
    :param result:
    :param reason:
    :param data:
    :param params:
    :param wait_result:
    :param directive:
    :param user_token:
    # :param ignore_error:
    :param time_operation:
    :param id_test:
    :param show_params:
    :param not_equal:
    :return:
    """
    # подсчитаем количество сделанных тестов
    global q_test
    global q_error
    global max_len_message
    global mas_error
    q_test += 1
    max_len_message = max(max_len_message, len(message))

    # если от Rest получен ответ True, то выводить ответ не будем
    if result:
        data = ''

    # если есть параметры, то приведем их в строку с кодировкой
    if params != '':
        params = 'params = ' + json.dumps(params, ensure_ascii=False)
    if not show_params:
        params = ''

    # определим значение поля "ответ от Rest"
    st_result = boolean_str(result, '[ok]    ', '[Error] ')

    # время выполнения операции
    st_time = dop_st("%.3f" % time_operation, 5, to_right=False),

    # определим пройден ли тест
    result_test = result
    if wait_result is not None:
        result_test = result == wait_result

    if reason == st_error:  # это может быть прерывание от обмена Rest
        st_test_result = '[FAIL]'
    else:
        st_test_result = '[' + boolean_str(result_test, ' Ok ', 'FAIL') + ']'

    # подсчитаем количество не пройденных тестов
    if st_test_result == '[FAIL]':
        q_error += 1
        mas_error.append(q_test)

    if id_test is not None:
        st_number = str(id_test)
    else:
        st_number = ''
    st_number = dop_st(st_number, 5, to_right=False)
    reason = '[' + reason + ']'
    if not_equal:
        reason = reason + ' not equal'

    # теперь можно и напечатать
    print(dop_st(str(q_test), 3, to_right=False),
          st_number,
          dop_st(tek_proc, 16),  # источник теста
          st_test_result,  # результат теста
          dop_st(directive, 6),  # директива теста
          is_token(user_token),  # использование токена
          st_result,  # статус результата выполнения запроса к Rest
          st_time[0],
          dop_st(message, 40),  # посланная команда
          dop_st(reason, 32),  # статус кода ответа Rest с расшифровкой
          data,  # полученные от Rest данные в случае ошибки Rest
          params,  # использованные в тесте параметры BODY ключ params
          flush=True
          )
