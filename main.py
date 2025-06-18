from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import FileResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict
import fitz  # PyMuPDF
import os
import uuid
import json
import re
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
    referencias: str = Form(...),
    exclusiones: str = Form("{}")  # Diccionario en formato JSON con exclusiones
):
    try:
        referencias = json.loads(referencias)
        exclusiones = json.loads(exclusiones)
    except Exception:
        return {"error": "No se pudo leer referencias o exclusiones"}

    columna_x = {}
    resultados = {ref: [] for ref in referencias}
    filename = file.filename
    temp_pdf = f"/tmp/{filename}"

    # Guardar archivo temporalmente
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
                                if texto not in exclusiones.get(ref, []):
                                    resultados[ref].append(texto)

    # Detectar códigos tipo NIE/NIF en columna "NIF/CIF"
    nie_patron = re.compile(r"[XY]\d{7}W")
    nie_encontrados = set()
    if "NIF/CIF" in resultados:
        for valor in resultados["NIF/CIF"]:
            if nie_patron.fullmatch(valor):
                nie_encontrados.add(valor)

    # Normalizar longitud
    max_len = max(len(vals) for vals in resultados.values())
    for ref in referencias:
        while len(resultados[ref]) < max_len:
            resultados[ref].append("")

    # Crear Excel
    wb = Workbook()
    ws = wb.active
    ws.title = "Resultados"
    ws.append(referencias)
    for fila in zip(*[resultados[ref] for ref in referencias]):
        ws.append(list(fila))

    output_path = f"/tmp/resultado_{uuid.uuid4().hex}.xlsx"
    wb.save(output_path)

    headers = {}
    if nie_encontrados:
        advertencia = "¡Cuidado con estos NIE/NIF! Podrían no estar presentes en el Excel: " + ", ".join(sorted(nie_encontrados))
        headers["X-NIE-WARNINGS"] = advertencia

    return FileResponse(
        output_path,
        filename="resultado.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=headers
    )
