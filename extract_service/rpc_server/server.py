import io
import json
import time
from typing import IO
import pika

from ..extractor.pdf import convert_pdf
from .config import rpc_cfg

connection = pika.BlockingConnection(
    pika.ConnectionParameters(
        host=rpc_cfg.host,
        port=rpc_cfg.port,
        credentials=pika.PlainCredentials(
            rpc_cfg.user,
            rpc_cfg.password
        )
    )
)

channel = connection.channel()

channel.queue_declare(queue='pdf')
channel.queue_declare(queue='docx')

def extract_text(file: IO, file_type: str):
    if file_type == 'pdf':
        return convert_pdf(file)
    if file_type == 'docx':
        return 'docx'
    return 'other'


def on_request(ch, method, properties, body, file_type='pdf'):
    request = io.BytesIO(body)
    print(f'Received request for {file_type}')
    try:
        response = extract_text(request, file_type)
    except Exception as e:
        response = [{'messsage': str(e)}, {'message': 'eof'}]
    for page in response:
        ch.basic_publish(
            exchange='',
            routing_key=properties.reply_to,
            properties=pika.BasicProperties(
                correlation_id=properties.correlation_id
            ),
            body=json.dumps(page)
        )
        print(f"send page with message {page.get('message')}")
    ch.basic_ack(delivery_tag=method.delivery_tag)

def func_on_queue(file_type='pdf'):
    def on_queue(ch, method, properties, body):
        on_request(ch, method, properties, body, file_type)
    return on_queue

def start_server():
    channel.basic_consume(queue='pdf', on_message_callback=func_on_queue('pdf'))
    channel.basic_consume(queue='docx', on_message_callback=func_on_queue('docx'))
    print('Awaiting RPC requests')
    while True:
        try:
            channel.start_consuming()
        except pika.exceptions.AMQPConnectionError as e:
            print(f'Connection error: {e}, retrying in 10 seconds...')
            time.sleep(10)
        except ConnectionError as e:
            raise e
        