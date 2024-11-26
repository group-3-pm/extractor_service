import json
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

channel.queue_declare(queue=rpc_cfg.queue)

def extract_text(file: IO, file_type: str):
    if file_type == 'pdf':
        return convert_pdf(file.name)
    if file_type == 'docx':
        return 'docx'
    return 'other'


def on_request(ch, method, properties, body):
    request = json.loads(body)
    try:
        response = extract_text(request['file'], request['file_type'])
    except Exception as e:
        response = [f'Error: {e}']
    for page in response:
        ch.basic_publish(
            exchange='',
            routing_key=properties.reply_to,
            properties=pika.BasicProperties(
                correlation_id=properties.correlation_id
            ),
            body=json.dumps(page)
        )
    ch.basic_publish(
        exchange='',
        routing_key=properties.reply_to,
        properties=pika.BasicProperties(
            correlation_id=properties.correlation_id
        ),
        body=json.dumps('end')
    )
    ch.basic_ack(delivery_tag=method.delivery_tag)


def start_server():
    channel.basic_consume(queue=rpc_cfg.queue, on_message_callback=on_request)
    print('Awaiting RPC requests')
    channel.start_consuming()