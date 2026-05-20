import streamlit as st
from PIL import Image
from io import BytesIO
from datetime import datetime
import pandas as pd
import tempfile
import os

# PDF
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Image as RLImage
)

from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4

# GEOLOCATION
from streamlit_geolocation import streamlit_geolocation

# ==========================================
# CONFIG
# ==========================================

st.set_page_config(
    page_title="Relatório Fotográfico",
    layout="wide"
)

st.title("📍 Relatório Fotográfico Inteligente")

# ==========================================
# SESSION STATE
# ==========================================

if "registros" not in st.session_state:
    st.session_state.registros = []

# ==========================================
# GEOLOCALIZAÇÃO
# ==========================================

st.subheader("📡 Captura de Localização")

location = streamlit_geolocation()

latitude = None
longitude = None

if location:

    latitude = location["latitude"]
    longitude = location["longitude"]

    st.success("Localização capturada!")

    st.write(f"Latitude: {latitude}")
    st.write(f"Longitude: {longitude}")

else:
    st.warning("Permita o acesso à localização do navegador.")

# ==========================================
# CAPTURA DA FOTO
# ==========================================

st.subheader("📸 Captura de Foto")

foto = st.camera_input("Tire uma foto")

# ==========================================
# PREVIEW
# ==========================================

if foto:

    imagem = Image.open(foto)

    st.subheader("🖼 Pré-visualização")

    st.image(
        imagem,
        use_container_width=True
    )

    nome_apontamento = st.text_input(
        "Nome do apontamento",
        value=f"Apontamento {len(st.session_state.registros)+1}"
    )

    data_hora = datetime.now().strftime(
        "%d-%m-%Y %H:%M:%S"
    )

    # ==========================================
    # CONFIRMAR FOTO
    # ==========================================

    if st.button("✅ Confirmar Foto"):

        nome_arquivo = (
            f"{nome_apontamento.replace(' ', '_')}_"
            f"{datetime.now().strftime('%d-%m-%Y_%H-%M-%S')}"
        )

        maps_link = None

        if latitude and longitude:

            maps_link = (
                f"https://www.google.com/maps?q="
                f"{latitude},{longitude}"
            )

        registro = {
            "apontamento": nome_apontamento,
            "nome_arquivo": nome_arquivo,
            "imagem": imagem.copy(),
            "latitude": latitude,
            "longitude": longitude,
            "maps_link": maps_link,
            "data_hora": data_hora
        }

        st.session_state.registros.append(registro)

        st.success("Foto adicionada ao relatório!")

# ==========================================
# SIDEBAR
# ==========================================

st.sidebar.title("📋 Relatório")

st.sidebar.success(
    f"{len(st.session_state.registros)} fotos adicionadas"
)

# ==========================================
# PREVIEW RELATÓRIO
# ==========================================

if st.session_state.registros:

    st.subheader("📑 Prévia do Relatório")

    remover_index = None

    for idx, reg in enumerate(st.session_state.registros):

        st.markdown(f"## {reg['apontamento']}")

        col1, col2 = st.columns([1, 1])

        with col1:

            st.image(
                reg["imagem"],
                use_container_width=True
            )

        with col2:

            st.write(f"📷 {reg['nome_arquivo']}")

            st.write(f"🕒 {reg['data_hora']}")

            if reg["latitude"] and reg["longitude"]:

                st.write(f"📍 Latitude: {reg['latitude']}")
                st.write(f"📍 Longitude: {reg['longitude']}")

                st.markdown(
                    f"""
                    [🌎 Abrir no Google Maps]({reg['maps_link']})
                    """
                )

            else:

                st.error("Sem coordenadas GPS")

            if st.button(
                f"🗑 Remover {idx+1}"
            ):
                remover_index = idx

        st.divider()

    # REMOVE ITEM
    if remover_index is not None:

        st.session_state.registros.pop(remover_index)

        st.rerun()

# ==========================================
# GERAR EXCEL
# ==========================================

def gerar_excel(registros):

    df = pd.DataFrame([
        {
            "Apontamento": r["apontamento"],
            "Arquivo": r["nome_arquivo"],
            "Latitude": r["latitude"],
            "Longitude": r["longitude"],
            "Data/Hora": r["data_hora"],
            "Google Maps": r["maps_link"]
        }
        for r in registros
    ])

    output = BytesIO()

    with pd.ExcelWriter(
        output,
        engine="openpyxl"
    ) as writer:

        df.to_excel(
            writer,
            index=False
        )

    return output.getvalue()

# ==========================================
# GERAR PDF
# ==========================================

def gerar_pdf(registros):

    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4
    )

    styles = getSampleStyleSheet()

    elementos = []

    for reg in registros:

        elementos.append(
            Paragraph(
                f"<b>{reg['apontamento']}</b>",
                styles["Heading2"]
            )
        )

        elementos.append(
            Spacer(1, 10)
        )

        elementos.append(
            Paragraph(
                reg["nome_arquivo"],
                styles["Normal"]
            )
        )

        elementos.append(
            Paragraph(
                reg["data_hora"],
                styles["Normal"]
            )
        )

        elementos.append(
            Spacer(1, 10)
        )

        # IMAGEM TEMPORÁRIA
        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=".jpg"
        ) as tmp:

            caminho = tmp.name

            reg["imagem"].save(
                caminho,
                format="JPEG"
            )

        img = RLImage(
            caminho,
            width=350,
            height=260
        )

        elementos.append(img)

        elementos.append(
            Spacer(1, 10)
        )

        if reg["latitude"] and reg["longitude"]:

            elementos.append(
                Paragraph(
                    f"Latitude: {reg['latitude']}",
                    styles["Normal"]
                )
            )

            elementos.append(
                Paragraph(
                    f"Longitude: {reg['longitude']}",
                    styles["Normal"]
                )
            )

            link = (
                f'<link href="{reg["maps_link"]}">'
                f'Abrir localização no Google Maps'
                f'</link>'
            )

            elementos.append(
                Paragraph(
                    link,
                    styles["Normal"]
                )
            )

        else:

            elementos.append(
                Paragraph(
                    "Sem coordenadas GPS",
                    styles["Normal"]
                )
            )

        elementos.append(
            Spacer(1, 30)
        )

    doc.build(elementos)

    # REMOVE TEMP FILES
    for arq in os.listdir(tempfile.gettempdir()):

        if arq.endswith(".jpg"):

            try:
                os.remove(
                    os.path.join(
                        tempfile.gettempdir(),
                        arq
                    )
                )
            except:
                pass

    return buffer.getvalue()

# ==========================================
# GERAR RELATÓRIOS
# ==========================================

if st.session_state.registros:

    st.subheader("📤 Gerar Relatórios")

    col1, col2 = st.columns(2)

    with col1:

        excel_bytes = gerar_excel(
            st.session_state.registros
        )

        st.download_button(
            label="📥 Baixar Excel",
            data=excel_bytes,
            file_name="relatorio_fotografico.xlsx",
            mime=(
                "application/vnd.openxmlformats-officedocument"
                ".spreadsheetml.sheet"
            )
        )

    with col2:

        pdf_bytes = gerar_pdf(
            st.session_state.registros
        )

        st.download_button(
            label="📄 Baixar PDF",
            data=pdf_bytes,
            file_name="relatorio_fotografico.pdf",
            mime="application/pdf"
        )
