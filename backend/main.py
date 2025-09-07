from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import PyPDF2
import docx
import requests 
import json

app = FastAPI()
def query_ollama_stream(prompt: str):
    """
    Stream response from Ollama line by line.
    If Ollama does not support streaming, simulate streaming here.
    """
    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={"model": "llama3", "prompt": prompt},
            stream=True,
            timeout=300
        )
        buffer = ""
        for chunk in response.iter_lines():
            if chunk:
                chunk_str = chunk.decode("utf-8").strip()
                try:
                    data = json.loads(chunk_str)
                    if "response" in data:
                        buffer += data["response"]
                        while "\n" in buffer:
                            line, buffer = buffer.split("\n", 1)
                            yield line + "\n"
                except:
                    pass
        if buffer:
            yield buffer + "\n"

        if not buffer:
            yield "No response received from Ollama.\n"

    except Exception as e:
        yield f"Error contacting Ollama: {e}\n"
class ResumeInput(BaseModel):
    text: str
@app.post("/analyze-text-stream")
async def analyze_text_stream(data: ResumeInput):
    prompt = f"""
You are a helpful and friendly resume coach.
Give feedback that is average in length not too short and not too long.
Point out strengths, mistakes, and improvements.
Use clear, positive, and constructive language.
Resume text:
{data.text}
"""
    return StreamingResponse(query_ollama_stream(prompt), media_type="text/plain")
@app.post("/analyze-file-stream")
async def analyze_doc_stream(file: UploadFile = File(...)):
    if file.content_type == "application/pdf":
        pdf_reader = PyPDF2.PdfReader(file.file)
        text = "".join([page.extract_text() or "" for page in pdf_reader.pages])
    elif file.content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        doc = docx.Document(file.file)
        text = "\n".join([para.text for para in doc.paragraphs])
    else:
        raise HTTPException(status_code=400, detail="Only PDF or DOCX files allowed")
    prompt = f"""
You are a helpful and friendly resume coach.
Give feedback that is average in length  not too short and not too long.
Point out strengths, mistakes, and improvements.
Use clear, positive, and constructive language.

Resume text:
{text}
"""
    return StreamingResponse(query_ollama_stream(prompt), media_type="text/plain")
