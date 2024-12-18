import io
import json
import os
import tempfile
import time
import traceback
from typing import IO
import pika

from extractor.docx import convert_docx_to_md

from extractor.pdf import convert_pdf
from rpc_server.config import rpc_cfg

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

def extract_text(file: bytes, file_type: str):
    if file_type == 'pdf':
        file = io.BytesIO(file)
        return convert_pdf(file)
    if file_type == 'docx':
        with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as temp_file:
            temp_file.write(file)
            temp_file_path = temp_file.name
        print(f"Temp file path: {temp_file_path}")
        return convert_docx_to_md(temp_file_path)
    return [{"message": "Invalid file type"}]


def on_request(ch, method, properties, body, file_type='pdf'):
    request = body
    print(f'Received request for {file_type}')
    try:
        response = extract_text(request, file_type)
    except Exception as e:
        response = [{'message': f"Failed to extract: {e}"}, {'message': 'eof'}]
        traceback.print_exc()
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
    ch.basic_publish(
        exchange='',
        routing_key=properties.reply_to,
        properties=pika.BasicProperties(
            correlation_id=properties.correlation_id
        ),
        body=json.dumps({'message': 'eof'})
    )
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
        