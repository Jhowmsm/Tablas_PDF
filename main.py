from fastapi import FastAPI, UploadFile, File
from fastapi.responses import FileResponse
import fitz  # PyMuPDF
import csv
import os

app = FastAPI()

@app.post("/procesar/")
async def procesar_pdf(file: UploadFile = File(...)):
    filename = file.filename
    temp_pdf = f"/tmp/{filename}"

    with open(temp_pdf, "wb") as f:
        f.write(await file.read())

    referencias = [
        "Resultado Búsqueda",
        "Situación Admva.",
        "Nombre/Razón Social",
        "NIF/CIF"
    ]

    palabras_ignoradas = {
        "Resultado Búsqueda": ["Resultado Búsqueda", "Total", "Resultado"],
        "Situación Admva.": ["Situación Admva.", "Verificado", "Pendiente"],
        "Nombre/Razón Social": ["Nombre/Razón Social", "Cliente", "Empresa"],
        "NIF/CIF": ["NIF/CIF", "Identificación", "Documento"]
    }

    columna_x = {}
    resultados = {ref: [] for ref in referencias}

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
                                if texto not in palabras_ignoradas[ref]:
                                    resultados[ref].append(texto)

    csv_path = f"/tmp/resultados.csv"
    with open(csv_path, mode='w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(referencias)
        filas = list(zip(*[resultados[ref] for ref in referencias]))
        writer.writerows(filas)

    return FileResponse(csv_path, filename="resultado.csv", media_type="text/csv")
