import json
from typing import IO
from fastapi import UploadFile
import pika
import uuid


class FileRpcClient(object):

    def __init__(self, file_type):
        self.connection = pika.BlockingConnection(
            pika.ConnectionParameters(
                host='localhost',
                port=5672,
                credentials=pika.PlainCredentials(
                    'user',
                    'password'
                )
            )
        )


        self.channel = self.connection.channel()

        result = self.channel.queue_declare(queue='', exclusive=True)
        self.callback_queue = result.method.queue

        self.channel.basic_consume(
            queue=self.callback_queue,
            on_message_callback=self.on_response,
            auto_ack=True)

        self.response = None
        self.corr_id = None

    def on_response(self, ch, method, props, body):
        if self.corr_id == props.correlation_id:
            print("Received")
            self.response = body

    def call(self, file: bytes):
        self.response = None
        self.corr_id = str(uuid.uuid4())
        self.channel.basic_publish(
            exchange='',
            routing_key='pdf',
            properties=pika.BasicProperties(
                reply_to=self.callback_queue,
                correlation_id=self.corr_id,
            ),
            body=file
            )
        print("sent")

        while True:
            self.connection.process_data_events(time_limit=None)
            if self.response is not None:
                result = json.loads(self.response)
                yield json.dumps(result)
                if result.get("message") == "eof":
                    break
                self.response = None


def extract_text(file: bytes):
    client = FileRpcClient('pdf')
    result = client.call(file)
    return result