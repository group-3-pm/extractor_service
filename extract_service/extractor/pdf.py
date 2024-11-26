import os
import dotenv


from .utils import markdown_to_csv
dotenv.load_dotenv()

from marker.models import load_all_models
from .pdf_convertor.convert import custom_convert_pdf

import pprint

model_lst = load_all_models()

def convert_pdf(fpath):
    return custom_convert_pdf(fpath, model_lst)

if __name__ == '__main__':
    fpath = './.data/invoicesample.pdf'
    txt, images, metadata, table_data = convert_pdf(fpath)
    try:
        os.removedirs('./.data/test')
    except:
        print('No such directory to remove')
        pass
    os.makedirs('./.data/test', exist_ok=True)
    with open('./.data/test/test.md', 'w', encoding='utf-8') as f:
        f.write(txt)
    with open('./.data/test/table.json', 'w', encoding='utf-8') as f:
        f.write(pprint.pformat(table_data))
    for page in table_data:
        for table in page['tables']:
            with open(f'./.data/test/table_{table["page_number"]}_{table["table_index"]}.csv', 'w', encoding='utf-8') as f:
                f.write(markdown_to_csv(table["content"]))
    for pnum, img in images.items():
        img.save(f'./.data/test/{pnum}.png', format='PNG')
    pprint.pprint(metadata)
    