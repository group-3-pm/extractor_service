from extractor.pdf import load_models, model_lst
from rpc_server.server import start_server
import traceback

def main():
    try:
        model_lst = load_models()
        print('Models loaded')
        start_server()
    except Exception as e:
        print(f'Error: {e}')
        traceback.print_exc()
    
if __name__ == '__main__':
    main()