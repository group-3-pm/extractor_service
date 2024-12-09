from .extractor.pdf import load_models
from .rpc_server.server import start_server

def main():
    try:
        load_models()
        print('Models loaded')
        start_server()
    except Exception as e:
        print(f'Error: {e}')
    
if __name__ == '__main__':
    main()