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

# =====================================================
# CONFIG
# =====================================================

st.set_page_config(
    page_title="Relatório Fotográfico",
    layout="centered"
)

st.title("Relatório Fotográfico")

# =====================================================
# SESSION STATE
# =====================================================

if "registros" not in st.session_state:
    st.session_state.registros = []

if "finalizar" not in st.session_state:
    st.session_state.finalizar = False

# =====================================================
# CAPTURA GEOLOCALIZAÇÃO
# =====================================================

st.subheader("1️⃣ Capturar localização")

location = streamlit_geolocation()

latitude = None
longitude = None

if location:

    latitude = location.get("latitude")
    longitude = location.get("longitude")

if latitude and longitude:

    st.success("📡 Localização capturada")

    st.write(f"Latitude: {latitude}")
    st.write(f"Longitude: {longitude}")

else:

    st.warning(
        """
        Permita o acesso à localização do navegador.
        
        Android:
        Configurações → Localização → Permitir
        
        Chrome:
        Permitir acesso à localização
        """
    )

# =====================================================
# FOTO
# =====================================================

st.subheader("2️⃣ Tirar foto")

foto = st.camera_input("Capturar imagem")

# =====================================================
# PREVIEW DA FOTO
# =====================================================

if foto:

    imagem = Image.open(foto)

    st.subheader("3️⃣ Confirmar foto")

    st.image(
        imagem,
        use_container_width=True
    )

    nome_apontamento = st.text_input(
        "Nome do apontamento",
        value=f"Apontamento {len(st.session_state.registros)+1}"
    )

    observacao = st.text_area(
        "Observação"
    )

    if st.button("✅ Adicionar Foto"):

        data_hora = datetime.now().strftime(
            "%d/%m/%Y %H:%M:%S"
        )

        maps_link = None

        if latitude and longitude:

            maps_link = (
                f"https://www.google.com/maps?q="
                f"{latitude},{longitude}"
            )

        registro = {
            "apontamento": nome_apontamento,
            "observacao": observacao,
            "imagem": imagem.copy(),
            "latitude": latitude,
            "longitude": longitude,
            "maps_link": maps_link,
            "data_hora": data_hora
        }

        st.session_state.registros.append(registro)

        st.success("📸 Foto adicionada!")

        st.rerun()

# =====================================================
# FOTOS ADICIONADAS
# =====================================================

if st.session_state.registros:

    st.subheader("4️⃣ Fotos adicionadas")

    remover = None

    for idx, reg in enumerate(st.session_state.registros):

        with st.expander(f"📷 {reg['apontamento']}"):

            st.image(
                reg["imagem"],
                width=300
            )

            st.write(f"🕒 {reg['data_hora']}")

            if reg["observacao"]:
                st.write(f"📝 {reg['observacao']}")

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
                f"🗑 Remover {idx}",
                key=f"rem_{idx}"
            ):
                remover = idx

    if remover is not None:

        st.session_state.registros.pop(remover)

        st.rerun()

# =====================================================
# FINALIZAR
# =====================================================

if st.session_state.registros:

    st.subheader("5️⃣ Finalizar")

    if st.button("📑 Visualizar Relatório"):

        st.session_state.finalizar = True

# =====================================================
# PRÉVIA RELATÓRIO
# =====================================================

if st.session_state.finalizar:

    st.header("📄 Prévia do Relatório")

    for idx, reg in enumerate(
        st.session_state.registros,
        start=1
    ):

        st.markdown(f"## {reg['apontamento']}")

        st.write(
            f"Foto {idx}_"
            f"{datetime.now().strftime('%d-%m-%Y')}"
        )

        st.image(
            reg["imagem"],
            use_container_width=True
        )

        if reg["observacao"]:
            st.write(f"📝 {reg['observacao']}")

        if reg["latitude"] and reg["longitude"]:

            st.markdown(
                f"""
                📍 [Abrir localização no Google Maps]({reg['maps_link']})
                """
            )

        else:

            st.error("Sem coordenadas GPS")

        st.divider()

# =====================================================
# EXCEL
# =====================================================

def gerar_excel(registros):

    df = pd.DataFrame([
        {
            "Apontamento": r["apontamento"],
            "Data": r["data_hora"],
            "Latitude": r["latitude"],
            "Longitude": r["longitude"],
            "Google Maps": r["maps_link"],
            "Observação": r["observacao"]
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

# =====================================================
# PDF
# =====================================================

def gerar_pdf(registros):

    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4
    )

    styles = getSampleStyleSheet()

    elementos = []

    for idx, reg in enumerate(
        registros,
        start=1
    ):

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
                f"Foto {idx}",
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

        # IMAGEM TEMP
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

        if reg["observacao"]:

            elementos.append(
                Paragraph(
                    f"Observação: {reg['observacao']}",
                    styles["Normal"]
                )
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

    return buffer.getvalue()

# =====================================================
# DOWNLOADS
# =====================================================

if st.session_state.finalizar:

    st.subheader("📥 Downloads")

    col1, col2 = st.columns(2)

    with col1:

        excel_bytes = gerar_excel(
            st.session_state.registros
        )

        st.download_button(
            label="📊 Baixar Excel",
            data=excel_bytes,
            file_name="relatorio.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    with col2:

        pdf_bytes = gerar_pdf(
            st.session_state.registros
        )

        st.download_button(
            label="📄 Baixar PDF",
            data=pdf_bytes,
            file_name="relatorio.pdf",
            mime="application/pdf"
        )
