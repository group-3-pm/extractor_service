import dotenv
dotenv.load_dotenv()

from marker.convert import convert_single_pdf
from marker.models import load_all_models

from surya.model.ordering.decoder import MBART_ATTENTION_CLASSES

if 'sdpa' not in MBART_ATTENTION_CLASSES:
    MBART_ATTENTION_CLASSES['sdpa'] = MBART_ATTENTION_CLASSES['eager']

model_lst = load_all_models(device="cpu", dtype="auto")

def convert_pdf(fpath):
    return convert_single_pdf(fpath, model_lst)

if __name__ == '__main__':
    fpath = '/.data/CV Nguyễn Cao Thanh.pdf'
    txt, _, _ = convert_pdf(fpath)
    with open('/.data/test.md', 'w', encoding='utf-8') as f:
        f.write(txt)