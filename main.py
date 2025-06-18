from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import fitz  # PyMuPDF
import os
import uuid
import json
import re
from openpyxl import Workbook

app = FastAPI()

# CORS para GitHub Pages
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
    exclusiones: str = Form("{}")
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

    with open(temp_pdf, "wb") as f:
        f.write(await file.read())

    # Buscar texto y NIEs
    nie_patron = re.compile(r"[XY]\d{7}W")
    nie_encontrados = set()

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
                                    if ref == "NIF/CIF" and nie_patron.fullmatch(texto):
                                        nie_encontrados.add(texto)

    # Normalizar columnas
    max_len = max(len(vals) for vals in resultados.values())
    for ref in referencias:
        while len(resultados[ref]) < max_len:
            resultados[ref].append("")

    # Crear Excel
    wb = Workbook()
    ws1 = wb.active
    ws1.title = "Resultados"
    ws1.append(referencias)
    for fila in zip(*[resultados[ref] for ref in referencias]):
        ws1.append(list(fila))

    # Hoja de advertencias si hay NIEs
    if nie_encontrados:
        ws2 = wb.create_sheet("Advertencias_NIE")
        ws2.append(["Advertencia"])
        ws2.append(["¡Cuidado con estos NIE/NIF! Podrían no estar presentes en el Excel."])
        for nie in sorted(nie_encontrados):
            ws2.append([nie])

    output_path = f"/tmp/resultado_{uuid.uuid4().hex}.xlsx"
    wb.save(output_path)

    return FileResponse(
        output_path,
        filename="resultado.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
