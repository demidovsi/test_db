import common
import time
"""
В конфигурации в ключе "directories_files" могут быть перечислены директории (через запятую), в которых находятся
файлы (неважно с каким расширением) с содержимым ответа (в формате json) на команду, которая определяется из
имени файла со следующими изменениями:
    - из начала имени файла удаляется заданная строка, которая указывается в конфигурации в ключе "prefix"
    - ^ заменяется на /
    - # заменяется на ?
В настоящее время обмен с REST производится без токена, директива GET, без параметров, а только end point.

Требуется инсталляция библиотеки requests. Это можно сделать в терминале PyCharm с помощью pip install requests. После
этого необходимо включить эту библиотеку в проект (File, Settings, Project, Python Interpreter и плюс эту
библиотеку).
"""


def show_list_test(array_files):
    for index in range(len(array_files)):
        end_point = array_files[index].replace(common.prefix, '').split('.')[0].replace('^', '/').replace('#', '?')
        print(index + 1, '-', end_point)


if __name__ == '__main__':
    if common.load_config():  # чтение конфигурационных параметров из файла config.json
        list_files = list()  # массив имен обрабатываемых файлов
        list_directories = list()  # массив директорий для обрабатываемых файлов
        for directory_file in common.directories_files:  # цикл по директориям с файлами
            array = common.load_files(directory_file)  # определение массива файлов из указанной директории
            for unit in array:  # цикл добавления тестируемых файлов в основной массив файлов и директорий
                list_files.append(unit)
                list_directories.append(directory_file)
        show_list_test(list_files)  # вывод списка возможных тестов
        t_begin = None
        while True:
            num = input('Введите номера тестов через запятую (h - показать список, ENTER - выход, 0 - все тесты)=')
            if num == '':
                # окончание работы с программой
                break
            if 'h' in num:
                show_list_test(list_files)  # вывод списка возможных тестов
                continue
            try:
                mas = []
                if ',' in num:  # задан список номеров тестов (будем надеяться)
                    array_num = num.split(',')
                    for unit in array_num:
                        if unit is not None and unit.strip() != '':
                            mas.append(int(unit))
                else:
                    num = int(num.strip())
                    # формирование списка проводимых тестов
                    if num == 0:  # если задан 0, то есть все тесты
                        for i in range(len(list_files)):
                            mas.append(i + 1)
                    else:
                        if num <= len(list_files):
                            mas.append(num)  # задан всего один тест
                if len(mas) > 0:
                    mas.sort()  # по возрастанию, не зависимо от порядка ввода номеров тестов
                    # время начала тестирования
                    t_begin = time.time()
                    # сброс характеристик проведения теста
                    common.clear_results()
                    # печать строк заголовка для читаемости лога тестирования
                    common.print_zag()
                    # цикл по тестируемым файлам
                    for num in mas:
                        file_test = list_files[num - 1]
                        # убираем prefix и расширение файла
                        message = file_test.replace(common.prefix, '').split('.')[0]
                        # заменяем спец символы (которые не допустимы в имени файлов) на символы end point
                        message = message.replace('^', '/').replace('#', '?')
                        # формирование типа запроса (последнее поле в end point), которое пойдет в распечатку
                        common.tek_proc = message.split('/')[-1].split('?')[0]
                        # выполнение запроса
                        common.make_command('GET',
                                            message,
                                            True,
                                            file_answer=list_directories[num - 1] + '/' + file_test,
                                            id_test='T' + str(num))
            except Exception as err:
                if num != 'h':
                    print(f'error occurred: {err}')
            if t_begin is not None:
                # время, занятое тестированием
                t_begin = time.time() - t_begin
                print('-------------', 'Окончание тестирования.', 'Результат последнего тестирования', '-------------')
                # печать результатов тестирования (количество тестов, количество ошибочных тестов,
                # длительность тестирования)
                print('count_test=' + str(common.q_test) + ';   ',
                      'count_fail=' + str(common.q_error) + ';   ',
                      'count_except=' + str(common.q_except) + ';   ',
                      'count_not_found=' + str(common.q_not_found) + ';  ',
                      'max_len_message=' + str(common.max_len_message) + ';  ',
                      'Затрачено на тест=' + "%.3f" % t_begin, 'сек')
                if len(common.mas_error) > 0:
                    print('Ошибки:', common.mas_error)
                print('всего сделано запросов=', common.q_request)
                print('\tstatus_code:', common.mas_codes)
                print('\tstatus_reason:', common.mas_codes_text)
