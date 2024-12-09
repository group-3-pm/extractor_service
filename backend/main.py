from fastapi import FastAPI, UploadFile
from fastapi.responses import StreamingResponse
import uvicorn

from rpc import extract_text

app = FastAPI()

@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.post("/convert_pdf")
async def convert_pdf(file: UploadFile):
    file_content = await file.read()
    return StreamingResponse(extract_text(file_content), media_type="application/json")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)