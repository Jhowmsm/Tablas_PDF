from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import fitz  # PyMuPDF
import csv
import os
import uuid

app = FastAPI()

# Habilita CORS para GitHub Pages
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://jhowmsm.github.io"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/procesar/")
async def procesar_pdf(
    file: UploadFile = File(...),
    referencia: str = Form(...)
):
    filename = file.filename
    temp_pdf = f"/tmp/{filename}"

    with open(temp_pdf, "wb") as f:
        f.write(await file.read())

    columna_x = None
    resultados = []

    with fitz.open(temp_pdf) as doc:
        for pagina in doc:
            bloques = pagina.get_text("dict")["blocks"]
            for bloque in bloques:
                for linea in bloque.get("lines", []):
                    for span in linea.get("spans", []):
                        texto = span["text"].strip()
                        x = span["bbox"][0]

                        if referencia in texto and columna_x is None:
                            columna_x = x
                        if columna_x is not None and abs(x - columna_x) <= 5:
                            resultados.append([texto])

    csv_path = f"/tmp/resultado_{uuid.uuid4().hex}.csv"
    with open(csv_path, mode='w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(["Valores de la columna"])
        writer.writerows(resultados)

    return FileResponse(csv_path, filename="resultado.csv", media_type="text/csv")
