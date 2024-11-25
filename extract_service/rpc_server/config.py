import os
import dotenv
dotenv.load_dotenv()

class RpcConfig:
    def __init__(self):
        self.host = os.getenv('RPC_HOST')
        self.port = os.getenv('RPC_PORT')   
        self.user = os.getenv('RPC_USER')
        self.password = os.getenv('RPC_PASSWORD')
        self.queue = os.getenv('RPC_QUEUE')
    
rpc_cfg = RpcConfig()