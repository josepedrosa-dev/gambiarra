import streamlit as st
from PIL import Image
from io import BytesIO
from datetime import datetime
import pandas as pd
import tempfile

# PDF
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Image as RLImage
)

from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4

# JS
from streamlit_js_eval import streamlit_js_eval

# =====================================================
# CONFIG
# =====================================================

st.set_page_config(
    page_title="Relatório Fotográfico GPS",
    layout="centered"
)

st.title("📍 Relatório Fotográfico")

# =====================================================
# SESSION
# =====================================================

if "registros" not in st.session_state:
    st.session_state.registros = []

# =====================================================
# GPS CONTÍNUO
# =====================================================

st.components.v1.html(
    """
    <script>

    if (!window.gpsStarted) {

        window.gpsStarted = true;

        navigator.geolocation.watchPosition(

            (position) => {

                const gps = {

                    latitude: position.coords.latitude,

                    longitude: position.coords.longitude,

                    accuracy: position.coords.accuracy,

                    timestamp: new Date().toISOString()

                };

                localStorage.setItem(
                    "gps_data",
                    JSON.stringify(gps)
                );

            },

            (error) => {

                console.log(error);

            },

            {

                enableHighAccuracy: true,

                maximumAge: 1000,

                timeout: 10000

            }

        );
    }

    </script>
    """,
    height=0
)

# =====================================================
# RECUPERA GPS
# =====================================================

gps = streamlit_js_eval(
    js_expressions="""
    JSON.parse(localStorage.getItem("gps_data"))
    """,
    key="gps_reader"
)

latitude = None
longitude = None
precisao = None

if gps:

    latitude = gps.get("latitude")
    longitude = gps.get("longitude")
    precisao = gps.get("accuracy")

# =====================================================
# STATUS GPS
# =====================================================

st.subheader("📡 Status GPS")

if latitude and longitude:

    st.success("✅ GPS ativo")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "Latitude",
            round(latitude, 6)
        )

    with col2:
        st.metric(
            "Longitude",
            round(longitude, 6)
        )

    with col3:
        st.metric(
            "Precisão",
            f"{round(precisao, 1)} m"
        )

else:

    st.error(
        """
        ❌ GPS não disponível
        
        Verifique:
        - Permissão de localização
        - GPS ativado
        - HTTPS habilitado
        """
    )

# =====================================================
# FOTO
# =====================================================

st.subheader("📸 Capturar Foto")

foto = st.camera_input(
    "Tire uma foto"
)

# =====================================================
# PROCESSAMENTO
# =====================================================

if foto:

    imagem = Image.open(foto)

    st.image(
        imagem,
        use_container_width=True
    )

    st.divider()

    st.subheader("📝 Informações")

    col1, col2 = st.columns(2)

    with col1:

        apontamento = st.text_input(
            "Nome do apontamento",
            value=f"Apontamento {len(st.session_state.registros)+1}"
        )

    with col2:

        responsavel = st.text_input(
            "Responsável"
        )

    descricao = st.text_area(
        "Descrição"
    )

    # =================================================
    # GPS DA FOTO
    # =================================================

    maps_link = None

    if latitude and longitude:

        maps_link = (
            f"https://www.google.com/maps?q="
            f"{latitude},{longitude}"
        )

        st.success(
            "📍 Coordenada vinculada à foto"
        )

        st.markdown(
            f"""
            [🌎 Abrir no Google Maps]({maps_link})
            """
        )

    else:

        st.warning(
            "⚠️ Foto será salva sem GPS"
        )

    # =================================================
    # SALVAR
    # =================================================

    if st.button(
        "✅ Adicionar ao Relatório",
        type="primary"
    ):

        registro = {

            "id": len(st.session_state.registros) + 1,

            "apontamento": apontamento,

            "responsavel": responsavel,

            "descricao": descricao,

            "imagem": imagem.copy(),

            "latitude": latitude,

            "longitude": longitude,

            "precisao": precisao,

            "maps_link": maps_link,

            "data_hora": datetime.now().strftime(
                "%d/%m/%Y %H:%M:%S"
            )
        }

        st.session_state.registros.append(
            registro
        )

        st.success(
            "📸 Foto adicionada!"
        )

        st.rerun()

# =====================================================
# RELATÓRIO
# =====================================================

if st.session_state.registros:

    st.divider()

    st.subheader("📑 Relatório")

    remover = None

    for idx, reg in enumerate(
        st.session_state.registros
    ):

        with st.expander(
            f"{reg['id']} • {reg['apontamento']}"
        ):

            st.image(
                reg["imagem"],
                use_container_width=True
            )

            st.write(
                f"👤 {reg['responsavel']}"
            )

            st.write(
                f"🕒 {reg['data_hora']}"
            )

            if reg["descricao"]:

                st.write(
                    f"📝 {reg['descricao']}"
                )

            if reg["latitude"]:

                st.write(
                    f"📍 Latitude: {reg['latitude']}"
                )

                st.write(
                    f"📍 Longitude: {reg['longitude']}"
                )

                st.write(
                    f"🎯 Precisão: ±{round(reg['precisao'],1)} m"
                )

                st.markdown(
                    f"""
                    [🌎 Abrir Localização]({reg['maps_link']})
                    """
                )

            else:

                st.error(
                    "Sem GPS"
                )

            if st.button(
                f"🗑 Remover {idx}",
                key=f"rem_{idx}"
            ):

                remover = idx

    if remover is not None:

        st.session_state.registros.pop(
            remover
        )

        st.rerun()

# =====================================================
# EXCEL
# =====================================================

def gerar_excel(registros):

    df = pd.DataFrame([

        {

            "ID": r["id"],

            "Apontamento": r["apontamento"],

            "Responsável": r["responsavel"],

            "Descrição": r["descricao"],

            "Latitude": r["latitude"],

            "Longitude": r["longitude"],

            "Precisão": r["precisao"],

            "Google Maps": r["maps_link"],

            "Data": r["data_hora"]

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

    for reg in registros:

        elementos.append(
            Paragraph(
                f"<b>{reg['apontamento']}</b>",
                styles["Heading2"]
            )
        )

        elementos.append(
            Paragraph(
                f"Responsável: {reg['responsavel']}",
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

        # =========================================
        # IMAGEM
        # =========================================

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

        # =========================================
        # DESCRIÇÃO
        # =========================================

        if reg["descricao"]:

            elementos.append(
                Paragraph(
                    f"Descrição: {reg['descricao']}",
                    styles["Normal"]
                )
            )

        # =========================================
        # GPS
        # =========================================

        if reg["latitude"]:

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

            elementos.append(
                Paragraph(
                    f"Precisão: ±{round(reg['precisao'],1)} metros",
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

if st.session_state.registros:

    st.divider()

    st.subheader("📥 Exportar")

    col1, col2 = st.columns(2)

    with col1:

        st.download_button(

            label="📊 Baixar Excel",

            data=gerar_excel(
                st.session_state.registros
            ),

            file_name=(
                f"relatorio_"
                f"{datetime.now().strftime('%d-%m-%Y')}.xlsx"
            ),

            mime=(
                "application/vnd.openxmlformats-"
                "officedocument.spreadsheetml.sheet"
            )
        )

    with col2:

        st.download_button(

            label="📄 Baixar PDF",

            data=gerar_pdf(
                st.session_state.registros
            ),

            file_name=(
                f"relatorio_"
                f"{datetime.now().strftime('%d-%m-%Y')}.pdf"
            ),

            mime="application/pdf"
        )

# =====================================================
# FOOTER
# =====================================================

st.divider()

st.caption(
    "📍 GPS contínuo via watchPosition()"
)
