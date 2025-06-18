from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import List
import fitz  # PyMuPDF
import os
import uuid
import json
from openpyxl import Workbook

app = FastAPI()

# CORS para frontend en GitHub Pages
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
    referencias: str = Form(...)
):
    try:
        referencias = json.loads(referencias)
    except Exception:
        return {"error": "No se pudo leer las referencias"}

    columna_x = {}
    resultados = {ref: [] for ref in referencias}
    filename = file.filename
    temp_pdf = f"/tmp/{filename}"

    # Guardar archivo PDF temporalmente
    with open(temp_pdf, "wb") as f:
        f.write(await file.read())

    # Procesar PDF
    with fitz.open(temp_pdf) as doc:
        for pagina in doc:
            bloques = pagina.get_text("dict")["blocks"]
            for bloque in bloques:
                for linea in bloque.get("lines", []):
                    for span in linea.get("spans", []):
                        texto = span["text"].strip()
                        x = span["bbox"][0]

                        for ref in referencias:
                            if ref in texto and ref not in columna_x:
                                columna_x[ref] = x
                            if ref in columna_x and abs(x - columna_x[ref]) <= 5:
                                resultados[ref].append(texto)

    # Normalizar longitud de columnas
    max_len = max(len(vals) for vals in resultados.values())
    for ref in referencias:
        while len(resultados[ref]) < max_len:
            resultados[ref].append("")

    # Crear Excel
    wb = Workbook()
    ws = wb.active
    ws.title = "Resultados"

    # Escribir encabezados
    ws.append(referencias)

    # Escribir filas
    for fila in zip(*[resultados[ref] for ref in referencias]):
        ws.append(list(fila))

    # Guardar archivo Excel
    excel_path = f"/tmp/resultado_{uuid.uuid4().hex}.xlsx"
    wb.save(excel_path)

    return FileResponse(excel_path, filename="resultado.xlsx", media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
