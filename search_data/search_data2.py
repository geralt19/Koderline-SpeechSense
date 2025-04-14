import argparse
import re
from datetime import datetime
from typing import NamedTuple

import json # <--- ДОБАВЛЕНО: Импорт библиотеки для работы с JSON

import grpc
from google.protobuf.field_mask_pb2 import FieldMask
# <--- ИЗМЕНЕНО: Импортируем MessageToDict вместо MessageToJson для удобства сохранения в JSON --->
from google.protobuf.json_format import MessageToDict
# from google.protobuf.json_format import MessageToJson # <-- Оригинальный импорт оставлен, но закомментирован

from yandex.cloud.speechsense.v1 import search_pb2
from yandex.cloud.speechsense.v1 import talk_service_pb2
from yandex.cloud.speechsense.v1 import talk_service_pb2_grpc

# --- Класс IntRangeFilter и функция parse_int_range остаются без изменений ---
class IntRangeFilter(NamedTuple):
    key: str
    lower_bound: int
    lb_inclusive: bool
    upper_bound: int
    ub_inclusive: bool

def parse_int_range(s: str) -> IntRangeFilter:
    pattern = r'(-?\d+)(<=|<)(\w+)(<=|<)(-?\d+)'
    match = re.match(pattern, s)
    if not match:
        raise ValueError(f"Не удалось разобрать диапазон целых чисел из: '{s}'")
    lower_bound = int(match.group(1))
    lower_bound_inclusive = match.group(2) == "<="
    key = match.group(3)
    upper_bound_inclusive = match.group(4) == "<="
    upper_bound = int(match.group(5))
    return IntRangeFilter(
        key=key,
        lower_bound=lower_bound,
        lb_inclusive=lower_bound_inclusive,
        upper_bound=upper_bound,
        ub_inclusive=upper_bound_inclusive
    )

# --- Функция build_search_request остается без изменений ---
# (Закомментированы строки добавления фильтров, так как ищем все)
def build_search_request(
        organization_id: str,
        space_id: str,
        connection_id: str,
        project_id: str,
        query=None,
        from_date=None,
        to_date=None,
        match_filter=None,
        classifier_filter=None,
        page_size=100,
        page_token='') -> talk_service_pb2.SearchTalkRequest:
    request = talk_service_pb2.SearchTalkRequest(
        organization_id=organization_id,
        space_id=space_id,
        connection_id=connection_id,
        project_id=project_id,
        page_size=page_size,
        page_token=page_token
    )
    # # Добавление запроса полнотекстового поиска (ПОКА ЗАКОММЕНТИРОВАНО)
    # if query:
    #     request.query.text = query
    # # Добавление фильтра по дате (ПОКА ЗАКОММЕНТИРОВАНО)
    # if from_date:
    #     date_filter = search_pb2.DateRangeFilter()
    #     date_filter.from_value.FromDatetime(datetime.fromisoformat(from_date))
    #     request.filters.append(search_pb2.Filter(key="userMeta.date", date_range=date_filter))
    # if to_date:
    #     date_filter = search_pb2.DateRangeFilter()
    #     date_filter.to_value.FromDatetime(datetime.fromisoformat(to_date))
    #     request.filters.append(search_pb2.Filter(key="userMeta.date", date_range=date_filter))
    # # Добавление match-фильтра (ПОКА ЗАКОММЕНТИРОВАНО)
    # if match_filter:
    #     key, value = match_filter.split(':')
    #     any_match_filter = search_pb2.AnyMatchFilter()
    #     any_match_filter.values.append(value)
    #     request.filters.append(search_pb2.Filter(key=key, any_match=any_match_filter))
    # # Добавление фильтра классификатора (ПОКА ЗАКОММЕНТИРОВАНО)
    # if classifier_filter:
    #     filter_values = parse_int_range(classifier_filter)
    #     int_range_filter = search_pb2.IntRangeFilter()
    #     int_range_filter.from_value.value=filter_values.lower_bound
    #     int_range_filter.to_value.value=filter_values.upper_bound
    #     int_range_filter.bounds_inclusive.from_inclusive=filter_values.lb_inclusive
    #     int_range_filter.bounds_inclusive.to_inclusive=filter_values.ub_inclusive
    #     request.filters.append(
    #             search_pb2.Filter(key='talk.classifiers.' + filter_values.key + '.count', int_range=int_range_filter))
    return request

# <--- ИЗМЕНЕНО: Функция теперь не 'print_talks', а 'save_talks_to_json', и принимает имя файла --->
def save_talks_to_json(
        api_key: str,
        organization_id: str,
        space_id: str,
        connection_id: str,
        project_id: str,
        output_file: str, # <--- ДОБАВЛЕНО: Параметр для имени выходного файла
        query=None,
        from_date=None,
        to_date=None,
        match_filter=None,
        classifier_filter=None
):
    # --- Установка соединения с gRPC каналом (без изменений) ---
    credentials = grpc.ssl_channel_credentials()
    channel = grpc.secure_channel('api.speechsense.yandexcloud.net:443', credentials)
    talk_service_stub = talk_service_pb2_grpc.TalkServiceStub(channel)

    page_token = ''
    all_talks_data = [] # <--- ДОБАВЛЕНО: Список для хранения данных всех диалогов

    print("Начинаем получение данных по диалогам...")

    # --- Цикл для обхода страниц результатов поиска (без изменений) ---
    while True:
        # Собираем запрос поиска (фильтры пока отключены)
        search_request = build_search_request(
            organization_id=organization_id,
            space_id=space_id,
            connection_id=connection_id,
            project_id=project_id,
            # query=query, # Пока отключено
            # from_date=from_date, # Пока отключено
            # to_date=to_date, # Пока отключено
            # match_filter=match_filter, # Пока отключено
            # classifier_filter=classifier_filter, # Пока отключено
            page_token=page_token)

        # Выполняем поиск ID подходящих диалогов
        try:
            search_response = talk_service_stub.Search(search_request, metadata=(
                ('authorization', f'Api-Key {api_key}'),
            ))
        except grpc.RpcError as e:
            print(f"Ошибка gRPC при выполнении Search: {e.code()} - {e.details()}") 
            break

        page_token = search_response.next_page_token
        talk_ids_on_page = search_response.talk_ids

        if not talk_ids_on_page:
            print("На этой странице не найдено ID диалогов.") 
            if not page_token:
                 break
            else:
                 continue

        print(f"Найдено {len(talk_ids_on_page)} ID диалогов на этой странице. Запрашиваем полные данные...") 

        # --- Запрос полных данных для найденных ID диалогов ---
        fields_to_include = FieldMask(
            paths=['transcription', 'speech_statistics', 'silence_statistics',
                   'interrupts_statistics', 'conversation_statistics', 'points',
                   'text_classifiers', 'talk_fields', 'summarization', 'talk_state']) # Список маск для вывода

        get_request = talk_service_pb2.GetTalkRequest(
            organization_id=organization_id,
            space_id=space_id,
            connection_id=connection_id,
            project_id=project_id,
            talk_ids=talk_ids_on_page,
            results_mask=fields_to_include
        )

        try:
            get_response = talk_service_stub.Get(get_request, metadata=(
                ('authorization', f'Api-Key {api_key}'),
            ))
        except grpc.RpcError as e:
            print(f"Ошибка gRPC при выполнении Get: {e.code()} - {e.details()}") 
            break

        # --- Преобразование Protobuf сообщений в словари и добавление в список ---
        for talk_message in get_response.talk:
            # <--- ИЗМЕНЕНО: Преобразуем Protobuf сообщение в словарь --->
            talk_dict = MessageToDict(talk_message, preserving_proto_field_name=True)
            all_talks_data.append(talk_dict)
            # <--- ИЗМЕНЕНО: Убираем печать JSON в консоль --->
            # print(MessageToJson(talk, ensure_ascii=False)) # <-- Оригинальная строка печати закомментирована
            print(f"  Обработаны данные для диалога ID: {talk_message.id}") 

        # Если токен для следующей страницы пуст, выходим из цикла
        if not page_token:
            print("Больше страниц нет.") 
            break
        else:
            print("Переходим к следующей странице...") 

    # --- Сохранение всех собранных данных в JSON файл ---
    # <--- ДОБАВЛЕНО: Блок сохранения данных в файл --->
    if all_talks_data:
        try:
            with open(output_file, 'w', encoding='utf-8') as f: # Используем параметр функции output_file
                json.dump(all_talks_data, f, ensure_ascii=False, indent=4)
            print(f"\nУспешно сохранено данных по {len(all_talks_data)} диалогам в файл '{output_file}'") 
        except IOError as e:
            print(f"\nОшибка записи в файл '{output_file}': {e}") 
        except Exception as e:
            print(f"\nПроизошла непредвиденная ошибка при записи в файл: {e}") 
    else:
        print("\nНет данных для сохранения.") 

    print("Скрипт завершил работу.") 


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--key', required=True, help='API ключ или IAM токен', type=str)
    parser.add_argument('--organization-id', required=True, help='ID организации', type=str)
    parser.add_argument('--space-id', required=True, help='ID пространства', type=str)
    parser.add_argument('--connection-id', required=True, help='ID подключения', type=str)
    parser.add_argument('--project-id', required=True, help='ID проекта', type=str)
    parser.add_argument('--query', required=False, help='Запрос полнотекстового поиска', type=str)
    parser.add_argument('--match-filter', required=False, help='Простой match-фильтр в формате ключ:значение', type=str)
    parser.add_argument('--classifier-filter', required=False,
                        help='Диапазон для классификатора X в формате значение_от</<=X</<=значение_до', type=str)
    parser.add_argument('--before', required=False, help='Искать диалоги до временной метки', type=str)
    parser.add_argument('--after', required=False, help='Искать диалоги после временной метки', type=str)
    # <--- ДОБАВЛЕНО: Аргумент для имени выходного JSON файла --->
    parser.add_argument('--output-file', required=True, help='Путь к выходному JSON файлу', type=str)

    args = parser.parse_args()

    # <--- ИЗМЕНЕНО: Вызываем новую функцию save_talks_to_json вместо print_talks --->
    save_talks_to_json(
        args.key,
        args.organization_id,
        args.space_id,
        args.connection_id,
        args.project_id,
        args.output_file, # <--- ДОБАВЛЕНО: Передаем имя файла в функцию
        query=args.query,
        from_date=args.after,
        to_date=args.before,
        match_filter=args.match_filter,
        classifier_filter=args.classifier_filter
    )