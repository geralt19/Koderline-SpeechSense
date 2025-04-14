import argparse
import json
from typing import Dict
import grpc
import datetime

from yandex.cloud.speechsense.v1 import talk_service_pb2
from yandex.cloud.speechsense.v1 import talk_service_pb2_grpc
from yandex.cloud.speechsense.v1 import audio_pb2

# Для аутентификации с IAM-токеном замените параметр api_key на iam_token
def upload_talk(connection_id: int, metadata: Dict[str, str], api_key: str, audio_bytes: bytes):
   credentials = grpc.ssl_channel_credentials()
   channel = grpc.secure_channel('api.speechsense.yandexcloud.net:443', credentials)
   talk_service_stub = talk_service_pb2_grpc.TalkServiceStub(channel)

# Формирование запроса к API
   request = talk_service_pb2.UploadTalkRequest(
      metadata=talk_service_pb2.TalkMetadata(
         connection_id=str(connection_id),
         fields=metadata
      ),
      # Формат аудио — MP3
      audio=audio_pb2.AudioRequest(
         audio_metadata=audio_pb2.AudioMetadata(
            container_audio=audio_pb2.ContainerAudio(
               container_audio_type=audio_pb2.ContainerAudio.ContainerAudioType.CONTAINER_AUDIO_TYPE_MP3
            )
         ),
         audio_data=audio_pb2.AudioChunk(data=audio_bytes)
      )
   )
   # Тип аутентификации — API-ключ
   response = talk_service_stub.Upload(request, metadata=(
      ('authorization', f'Api-Key {api_key}'),
   # Для аутентификации с IAM-токеном передавайте заголовок
   #  ('authorization', f'Bearer {iam_token}'),
   ))

   # Вывести идентификатор диалога
   print(f'Dialog ID: {response.talk_id}')

if __name__ == '__main__':
   parser = argparse.ArgumentParser()
   parser.add_argument('--key', required=True, help='API key or IAM token', type=str)
   parser.add_argument('--connection-id', required=True, help='Connection ID', type=str)
   parser.add_argument('--audio-path', required=True, help='Audio file path', type=str)
   parser.add_argument('--meta-path', required=False, help='JSON with the dialog metadata', type=str, default=None)
   args = parser.parse_args()

   # Значения по умолчанию, если метаданные не указаны
   if args.meta_path is None:
      now = datetime.datetime.now().isoformat()
      metadata = {
         'operator_name': 'Operator',
         'operator_id': '1111',
         'client_name': 'Client',
         'client_id': '2222',
         'date': str(now),
         'date_from': '2023-09-13T17:30:00.000',
         'date_to': '2023-09-13T17:31:00.000',
         'direction_outgoing': 'true',
      }
   else:
      with open(args.meta_path, 'r') as fp:
         metadata = json.load(fp)

   with open(args.audio_path, 'rb') as fp:
      audio_bytes = fp.read()
   upload_talk(args.connection_id, metadata, args.key, audio_bytes)
