import json
import os
from typing import Dict, List
import dotenv
import base64
import io

dotenv.load_dotenv()

from marker.models import load_all_models
from .pdf_convertor.convert import custom_convert_pdf

import pprint

def load_models():
    global model_lst
    if os.getenv("MOCK") == "1":
      model_lst = []
    else:
      model_lst = load_all_models()
    return model_lst

def convert_image_to_base64(image):
    """Converts a PIL Image to a base64 string."""
    buffered = io.BytesIO()
    image.save(buffered, format="PNG") # or whichever format is appropriate
    img_str = base64.b64encode(buffered.getvalue()).decode()
    return img_str

def convert_to_img_list(imgs: Dict) -> List:
  img_list = list()
  for img_name in imgs:
    img_list.append({
        "name": img_name,
        "content": convert_image_to_base64(imgs[img_name])})
  return img_list

def convert_pdf(fpath):
  metadata = dict()

  if len(model_lst) == 0:
    abs = os.path.abspath(os.path.dirname(__file__))
    with open(f"{abs}/responses.json", "r") as f:
      data = json.load(f)
      for response in data:
        yield response
  else:
    for text, images, meta, tables, pnum, message in custom_convert_pdf(fpath, model_lst):
      page = {
          'page': pnum,
          'text': text,
          'images': convert_to_img_list(images),
          'tables': tables
          }
      if pnum == 0:
        metadata['languages'] = meta['languages']
        metadata['pages'] = meta['pages']
        metadata['filetype'] = meta['filetype']
        metadata['pdf_toc'] = meta['pdf_toc']
        yield {"metadata": metadata,
              "pnum": pnum,
              "page": page,
              "message": message
              }
        continue
      yield {
          "pnum": pnum,
          "page": page,
          "message": message
      }