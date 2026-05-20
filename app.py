import streamlit as st
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
import pandas as pd
from io import BytesIO
from datetime import datetime
import tempfile
import os

# PDF
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Image as RLImage,
    PageBreak
)
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4

# -----------------------------------
# CONFIG
# -----------------------------------

st.set_page_config(
    page_title="Relatório Fotográfico GPS",
    layout="wide"
)

st.title("📍 Relatório Fotográfico com Coordenadas")

# -----------------------------------
# FUNÇÕES
# -----------------------------------

def converter_para_decimal(valor):
    graus = float(valor[0])
    minutos = float(valor[1])
    segundos = float(valor[2])

    return graus + (minutos / 60) + (segundos / 3600)

def extrair_exif(imagem):
    try:
        return imagem._getexif()
    except:
        return None

def extrair_dados(imagem):
    exif = extrair_exif(imagem)

    if not exif:
        return None

    gps_info = {}
    data_foto = None

    for tag, value in exif.items():

        nome_tag = TAGS.get(tag, tag)

        # DATA FOTO
        if nome_tag == "DateTime":
            data_foto = value

        # GPS
        if nome_tag == "GPSInfo":

            for gps_tag in value:

                sub_tag = GPSTAGS.get(gps_tag, gps_tag)

                gps_info[sub_tag] = value[gps_tag]

    latitude = None
    longitude = None

    try:

        latitude = converter_para_decimal(
            gps_info["GPSLatitude"]
        )

        longitude = converter_para_decimal(
            gps_info["GPSLongitude"]
        )

        if gps_info["GPSLatitudeRef"] != "N":
            latitude = -latitude

        if gps_info["GPSLongitudeRef"] != "E":
            longitude = -longitude

    except:
        pass

    return {
        "latitude": latitude,
        "longitude": longitude,
        "data_foto": data_foto
    }

def gerar_link_maps(lat, lon):

    if lat and lon:
        return f"https://www.google.com/maps?q={lat},{lon}"

    return "Sem coordenada"

# -----------------------------------
# UPLOAD
# -----------------------------------

arquivos = st.file_uploader(
    "Envie as fotos",
    type=["jpg", "jpeg", "png"],
    accept_multiple_files=True
)

# -----------------------------------
# PROCESSAMENTO
# -----------------------------------

if arquivos:

    registros = []

    for i, arquivo in enumerate(arquivos, start=1):

        imagem = Image.open(arquivo)

        dados = extrair_dados(imagem)

        data_formatada = datetime.now().strftime("%d-%m-%Y")

        nome_foto = f"Foto_{i}_{data_formatada}"

        if dados:

            lat = dados["latitude"]
            lon = dados["longitude"]

            link_maps = gerar_link_maps(lat, lon)

        else:

            lat = None
            lon = None
            link_maps = "Sem coordenada"

        registros.append({
            "Apontamento": f"Apontamento {i}",
            "Nome Foto": nome_foto,
            "Latitude": lat,
            "Longitude": lon,
            "Link Maps": link_maps,
            "Imagem": imagem
        })

    # -----------------------------------
    # VISUALIZAÇÃO
    # -----------------------------------

    st.subheader("📷 Prévia")

    for reg in registros:

        st.markdown(f"## {reg['Apontamento']}")

        st.write(reg["Nome Foto"])

        st.image(
            reg["Imagem"],
            width=400
        )

        if reg["Latitude"] and reg["Longitude"]:

            st.markdown(
                f"""
                📍 [Abrir Localização no Google Maps]({reg['Link Maps']})
                """
            )

        else:

            st.error("Foto sem coordenada GPS")

        st.divider()

    # -----------------------------------
    # EXCEL
    # -----------------------------------

    df = pd.DataFrame([
        {
            "Apontamento": r["Apontamento"],
            "Nome Foto": r["Nome Foto"],
            "Latitude": r["Latitude"],
            "Longitude": r["Longitude"],
            "Google Maps": r["Link Maps"]
        }
        for r in registros
    ])

    excel_buffer = BytesIO()

    with pd.ExcelWriter(
        excel_buffer,
        engine="openpyxl"
    ) as writer:

        df.to_excel(
            writer,
            index=False
        )

    st.download_button(
        label="📥 Baixar Excel",
        data=excel_buffer.getvalue(),
        file_name="relatorio_fotos.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    # -----------------------------------
    # PDF
    # -----------------------------------

    pdf_buffer = BytesIO()

    doc = SimpleDocTemplate(
        pdf_buffer,
        pagesize=A4
    )

    elementos = []

    styles = getSampleStyleSheet()

    for reg in registros:

        elementos.append(
            Paragraph(
                f"<b>{reg['Apontamento']}</b>",
                styles["Heading2"]
            )
        )

        elementos.append(
            Paragraph(
                reg["Nome Foto"],
                styles["Normal"]
            )
        )

        elementos.append(
            Spacer(1, 10)
        )

        # Salva imagem temporária
        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=".jpg"
        ) as tmp:

            caminho_temp = tmp.name

            reg["Imagem"].save(
                caminho_temp,
                format="JPEG"
            )

        img_pdf = RLImage(
            caminho_temp,
            width=300,
            height=220
        )

        elementos.append(img_pdf)

        elementos.append(
            Spacer(1, 10)
        )

        if reg["Latitude"] and reg["Longitude"]:

            link = reg["Link Maps"]

            texto_link = f'''
            <link href="{link}">
            📍 Abrir localização no Google Maps
            </link>
            '''

            elementos.append(
                Paragraph(
                    texto_link,
                    styles["Normal"]
                )
            )

        else:

            elementos.append(
                Paragraph(
                    "Foto sem coordenada GPS",
                    styles["Normal"]
                )
            )

        elementos.append(
            Spacer(1, 30)
        )

    doc.build(elementos)

    # Remove imagens temporárias
    for arquivo in os.listdir(tempfile.gettempdir()):

        if arquivo.endswith(".jpg"):

            try:
                os.remove(
                    os.path.join(
                        tempfile.gettempdir(),
                        arquivo
                    )
                )
            except:
                pass

    st.download_button(
        label="📄 Baixar Relatório PDF",
        data=pdf_buffer.getvalue(),
        file_name="relatorio_fotografico.pdf",
        mime="application/pdf"
    )
