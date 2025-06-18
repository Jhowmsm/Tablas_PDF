from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import List
from openpyxl import Workbook
import fitz  # PyMuPDF
import csv
import os
import uuid
import json

app = FastAPI()

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
        referencias = json.loads(referencias)  # ✅ Solo una vez
    except Exception as e:
        return {"error": f"No se pudo leer las referencias: {str(e)}"}

    columna_x = {}
    resultados = {ref: [] for ref in referencias}
    filename = file.filename
    temp_pdf = f"/tmp/{filename}"

    with open(temp_pdf, "wb") as f:
        f.write(await file.read())

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

    excel_path = f"/tmp/resultado_{uuid.uuid4().hex}.xlsx"
    wb = Workbook()
    ws = wb.active

    # Escribir encabezados
    ws.append(referencias)

    # Escribir filas
    filas = zip(*[resultados[ref] for ref in referencias])
    for fila in filas:
        ws.append(fila)

    wb.save(excel_path)

    return FileResponse(excel_path, filename="resultado.xlsx", media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")