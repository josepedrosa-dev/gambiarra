import streamlit as st
from PIL import Image
from io import BytesIO
from datetime import datetime
import pandas as pd
import tempfile
import json
import base64

# PDF
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Image as RLImage,
    PageBreak
)

from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_CENTER
from reportlab.pdfgen import canvas

# JS
from streamlit_js_eval import streamlit_js_eval

# =====================================================
# CONFIG
# =====================================================

st.set_page_config(
    page_title="Relatório Fotográfico GPS",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Custom CSS for mobile optimization
st.markdown("""
    <style>
        * {
            box-sizing: border-box;
        }
        
        .main {
            padding: 1rem;
            max-width: 100%;
        }
        
        body {
            font-size: 16px;
        }
        
        /* Mobile optimized spacing */
        .section-header {
            font-size: 1.1rem;
            font-weight: 600;
            margin: 1rem 0 0.75rem 0;
            border-bottom: 1px solid #e0e0e0;
            padding-bottom: 0.5rem;
            color: #1f1f1f;
        }
        
        .info-box, .success-box, .warning-box {
            padding: 0.75rem;
            border-radius: 6px;
            border-left: 3px solid;
            margin: 0.5rem 0;
            font-size: 0.95rem;
            line-height: 1.4;
        }
        
        .success-box {
            background: #f1f8e9;
            border-left-color: #558b2f;
        }
        
        .warning-box {
            background: #fff3e0;
            border-left-color: #e65100;
        }
        
        .info-box {
            background: #f5f5f5;
            border-left-color: #0066cc;
        }
        
        .photo-item {
            background: #fafafa;
            border-radius: 8px;
            padding: 1rem;
            margin: 0.75rem 0;
        }
        
        /* Input fields mobile friendly */
        input, textarea, select {
            font-size: 16px !important;
            padding: 0.75rem !important;
            border-radius: 4px !important;
        }
        
        /* Button optimization */
        button {
            font-size: 0.95rem;
            padding: 0.75rem !important;
            min-height: 44px;
            border-radius: 4px;
        }
        
        /* Metric optimization */
        [data-testid="metric-container"] {
            background: #f5f5f5;
            border-radius: 6px;
            padding: 0.75rem;
            margin: 0.5rem 0;
        }
        
        /* Expander mobile friendly */
        [data-testid="expander"] {
            border: 1px solid #e0e0e0;
            border-radius: 6px;
            margin: 0.5rem 0;
        }
        
        /* Responsive grid */
        @media (max-width: 640px) {
            .main {
                padding: 0.75rem;
            }
            
            h1 {
                font-size: 1.5rem;
                margin-bottom: 1rem;
            }
            
            .section-header {
                font-size: 1rem;
                margin: 0.75rem 0 0.5rem 0;
            }
            
            [data-testid="column"] {
                min-width: 100% !important;
            }
            
            .photo-info {
                display: flex;
                flex-direction: column;
                gap: 0.5rem;
            }
        }
    </style>
""", unsafe_allow_html=True)

st.title("Relatório Fotográfico com GPS")

# =====================================================
# SESSION
# =====================================================

if "registros" not in st.session_state:
    st.session_state.registros = []

if "camera_key" not in st.session_state:
    st.session_state.camera_key = 0

# =====================================================
# PERSISTÊNCIA EM LOCALSTORAGE
# =====================================================

def codificar_imagem(imagem):
    """Converte PIL Image para base64"""
    buffer = BytesIO()
    imagem.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode()

def decodificar_imagem(base64_str):
    """Converte base64 para PIL Image"""
    try:
        img_data = base64.b64decode(base64_str)
        return Image.open(BytesIO(img_data))
    except:
        return None

def sincronizar_registros_para_storage():
    """Salva registros no localStorage"""
    registros_json = []
    for reg in st.session_state.registros:
        reg_dict = reg.copy()
        # Converte imagem para base64
        if "imagem" in reg_dict and reg_dict["imagem"]:
            reg_dict["imagem"] = codificar_imagem(reg_dict["imagem"])
        registros_json.append(reg_dict)
    
    # Script JS para salvar
    st.components.v1.html(
        f"""
        <script>
        localStorage.setItem("registros_gambiarra", JSON.stringify({json.dumps(registros_json)}));
        </script>
        """,
        height=0
    )

def carregar_registros_do_storage():
    """Carrega registros do localStorage"""
    registros_data = streamlit_js_eval(
        js_expressions="""
        JSON.parse(localStorage.getItem("registros_gambiarra") || "[]")
        """,
        key="load_registros"
    )
    
    if registros_data and isinstance(registros_data, list):
        registros_carregados = []
        for reg in registros_data:
            if "imagem" in reg and reg["imagem"]:
                reg["imagem"] = decodificar_imagem(reg["imagem"])
            registros_carregados.append(reg)
        return registros_carregados
    return []

# Carrega registros salvos ao iniciar
if not st.session_state.registros:
    st.session_state.registros = carregar_registros_do_storage()

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
gps_timestamp = None

if gps:
    latitude = gps.get("latitude")
    longitude = gps.get("longitude")
    precisao = gps.get("accuracy")
    gps_timestamp = gps.get("timestamp")

# =====================================================
# DADOS FIXOS DO RELATÓRIO
# =====================================================

st.markdown("<div class='section-header'>Informações Básicas</div>", unsafe_allow_html=True)

responsavel = st.text_input(
    "Responsável",
    placeholder="Nome do responsável",
    max_chars=100
)

medicao_fiscal = st.text_input(
    "Medição Fiscal",
    placeholder="Número ou referência",
    max_chars=100
)

# =====================================================
# STATUS GPS
# =====================================================

st.markdown("<div class='section-header'>Status do GPS</div>", unsafe_allow_html=True)

if latitude is not None and longitude is not None:
    col1, col2 = st.columns(2, gap="small")

    with col1:
        st.metric("Latitude", f"{round(float(latitude), 6)}°")

    with col2:
        st.metric("Longitude", f"{round(float(longitude), 6)}°")

    st.metric("Precisão", f"±{round(float(precisao), 1)} m" if precisao else "N/A")

    if gps_timestamp:
        st.caption(f"Última atualização: {gps_timestamp}")

else:
    st.markdown("""
        <div class='warning-box'>
            <strong>GPS não disponível</strong><br/>
            Ative o GPS, permita acesso à localização e use HTTPS.
        </div>
    """, unsafe_allow_html=True)

# =====================================================
# BLOQUEIO
# =====================================================

if not responsavel.strip() or not medicao_fiscal.strip():
    st.markdown("""
        <div class='warning-box'>
            <strong>Campos obrigatórios</strong><br/>
            Preencha "Responsável" e "Medição Fiscal".
        </div>
    """, unsafe_allow_html=True)
    st.stop()

# =====================================================
# FOTO
# =====================================================

st.markdown("<div class='section-header'>Capturar Foto</div>", unsafe_allow_html=True)

foto = st.camera_input(
    "Fotografe o local",
    key=f"camera_{st.session_state.camera_key}"
)

# =====================================================
# PROCESSAMENTO FOTO
# =====================================================

if foto:
    imagem = Image.open(foto).convert("RGB")

    st.markdown("<div class='photo-item'>", unsafe_allow_html=True)
    st.image(imagem, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div class='section-header'>Informações da Foto</div>", unsafe_allow_html=True)

    nome_apontamento = st.text_input(
        "Nome do Apontamento",
        value=f"Apontamento {len(st.session_state.registros) + 1}",
        max_chars=100
    )

    descricao = st.text_area(
        "Descrição / Observações",
        height=80,
        max_chars=500,
        placeholder="Adicione observações (opcional)"
    )

    # =================================================
    # GPS
    # =================================================

    maps_link = None

    if latitude is not None and longitude is not None:
        maps_link = f"https://www.google.com/maps?q={latitude},{longitude}"
        
        st.markdown("""
            <div class='success-box'>
                <strong>Coordenada vinculada</strong><br/>
                A localização será incluída nesta foto.
            </div>
        """, unsafe_allow_html=True)

        st.markdown("<div class='photo-info'>", unsafe_allow_html=True)
        st.text(f"Latitude: {latitude}")
        st.text(f"Longitude: {longitude}")

        if precisao is not None:
            st.text(f"Precisão: ±{round(float(precisao), 1)} m")

        if gps_timestamp:
            st.caption(f"GPS: {gps_timestamp}")
        
        st.markdown("</div>", unsafe_allow_html=True)

    else:
        st.markdown("""
            <div class='warning-box'>
                <strong>GPS não disponível</strong><br/>
                Esta foto será salva sem localização.
            </div>
        """, unsafe_allow_html=True)

    # =================================================
    # BOTÕES
    # =================================================

    col1, col2 = st.columns(2, gap="small")

    with col1:
        if st.button(
            "Adicionar Foto",
            type="primary",
            use_container_width=True,
            key="btn_add"
        ):
            if not nome_apontamento.strip():
                st.error("Informe o nome do apontamento")
            else:
                registro = {
                    "id": len(st.session_state.registros) + 1,
                    "responsavel": responsavel,
                    "medicao_fiscal": medicao_fiscal,
                    "nome_apontamento": nome_apontamento,
                    "descricao": descricao,
                    "imagem": imagem.copy(),
                    "latitude": latitude,
                    "longitude": longitude,
                    "precisao": precisao,
                    "gps_timestamp": gps_timestamp,
                    "maps_link": maps_link,
                    "data_hora": datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                }

                st.session_state.registros.append(registro)
                
                # Sincroniza com localStorage
                sincronizar_registros_para_storage()
                
                st.success("Foto adicionada com sucesso")

                st.session_state.camera_key += 1
                st.rerun()

    with col2:
        if st.button(
            "Cancelar",
            use_container_width=True,
            key="btn_cancel"
        ):
            st.session_state.camera_key += 1
            st.rerun()

# =====================================================
# RELATÓRIO
# =====================================================

if st.session_state.registros:
    st.markdown("<div class='section-header'>Fotos do Relatório</div>", unsafe_allow_html=True)

    st.info(f"{len(st.session_state.registros)} foto(s)")

    remover = None

    for idx, reg in enumerate(st.session_state.registros):
        with st.expander(f"{reg['id']} — {reg['nome_apontamento']}", expanded=False):
            st.image(reg["imagem"], use_container_width=True)

            st.markdown("<div class='photo-info'>", unsafe_allow_html=True)
            
            st.text(f"Data: {reg['data_hora']}")
            
            if reg["descricao"]:
                st.text(f"Descrição: {reg['descricao']}")

            if reg["latitude"] is not None and reg["longitude"] is not None:
                st.text(f"Latitude: {reg['latitude']}")
                st.text(f"Longitude: {reg['longitude']}")
                
                if reg.get("precisao") is not None:
                    st.text(f"Precisão: ±{round(float(reg['precisao']), 1)} m")
                
                if reg.get("gps_timestamp"):
                    st.caption(f"GPS: {reg['gps_timestamp']}")
                
                if reg.get("maps_link"):
                    st.markdown(f"[Abrir no Google Maps]({reg['maps_link']})")
            else:
                st.text("Sem coordenadas GPS")
            
            st.markdown("</div>", unsafe_allow_html=True)

            if st.button(
                f"Remover",
                key=f"rem_{idx}",
                use_container_width=True
            ):
                remover = idx

    if remover is not None:
        st.session_state.registros.pop(remover)
        # Sincroniza remoção com localStorage
        sincronizar_registros_para_storage()
        st.rerun()

# =====================================================
# EXCEL
# =====================================================

def gerar_excel(registros):
    df = pd.DataFrame([
        {
            "ID": r.get("id"),
            "Responsável": r.get("responsavel"),
            "Medição Fiscal": r.get("medicao_fiscal"),
            "Apontamento": r.get("nome_apontamento"),
            "Descrição": r.get("descricao"),
            "Latitude": r.get("latitude"),
            "Longitude": r.get("longitude"),
            "Precisão (m)": r.get("precisao"),
            "GPS Timestamp": r.get("gps_timestamp"),
            "Google Maps": r.get("maps_link"),
            "Data": r.get("data_hora")
        }
        for r in registros
    ])

    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False)

    return output.getvalue()

# =====================================================
# PDF
# =====================================================

def gerar_pdf(registros):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    
    # Estilo customizado para link
    link_style = ParagraphStyle(
        'LinkStyle',
        parent=styles['Normal'],
        fontSize=11,
        textColor='#0066CC',
        underline=True,
        spaceAfter=12,
        alignment=TA_CENTER
    )
    
    elementos = []

    # Cabeçalho
    elementos.append(Paragraph(
        "<b>RELATÓRIO FOTOGRÁFICO</b>",
        styles["Title"]
    ))

    elementos.append(Spacer(1, 12))

    elementos.append(Paragraph(
        f"<b>Responsável:</b> {registros[0].get('responsavel', '')}",
        styles["Normal"]
    ))

    elementos.append(Paragraph(
        f"<b>Medição Fiscal:</b> {registros[0].get('medicao_fiscal', '')}",
        styles["Normal"]
    ))

    elementos.append(Spacer(1, 20))

    # Fotos
    for idx, reg in enumerate(registros):
        if idx > 0:
            elementos.append(PageBreak())

        elementos.append(Paragraph(
            f"<b>{reg.get('nome_apontamento', '')}</b>",
            styles["Heading2"]
        ))

        elementos.append(Paragraph(
            f"Data: {reg.get('data_hora', '')}",
            styles["Normal"]
        ))

        elementos.append(Spacer(1, 12))

        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
            caminho = tmp.name
            reg["imagem"].save(caminho, format="JPEG")

        img = RLImage(caminho, width=400, height=300)
        img.hAlign = "CENTER"
        elementos.append(img)
        elementos.append(Spacer(1, 12))

        descricao = reg.get("descricao", "")
        if descricao:
            elementos.append(Paragraph(
                f"<b>Descrição:</b> {descricao}",
                styles["Normal"]
            ))

        latitude_reg = reg.get("latitude")
        longitude_reg = reg.get("longitude")

        if latitude_reg is not None and longitude_reg is not None:
            elementos.append(Paragraph(
                f"<b>Latitude:</b> {latitude_reg}",
                styles["Normal"]
            ))

            elementos.append(Paragraph(
                f"<b>Longitude:</b> {longitude_reg}",
                styles["Normal"]
            ))

            if reg.get("precisao") is not None:
                elementos.append(Paragraph(
                    f"<b>Precisão:</b> ±{round(float(reg['precisao']), 1)} metros",
                    styles["Normal"]
                ))

            gps_timestamp_reg = reg.get("gps_timestamp", "Não disponível")
            elementos.append(Paragraph(
                f"<b>GPS capturado em:</b> {gps_timestamp_reg}",
                styles["Normal"]
            ))

            maps_link_reg = reg.get("maps_link")
            if maps_link_reg:
                link_html = f'<link href="{maps_link_reg}" color="blue"><u><b>🗺️ Abrir localização no Google Maps</b></u></link>'
                elementos.append(Paragraph(link_html, link_style))

        else:
            elementos.append(Paragraph(
                "Sem coordenadas GPS",
                styles["Normal"]
            ))

        elementos.append(Spacer(1, 25))

    doc.build(elementos)
    return buffer.getvalue()

# =====================================================
# DOWNLOADS
# =====================================================

if st.session_state.registros:
    st.markdown("<div class='section-header'>Exportar Relatório</div>", unsafe_allow_html=True)

    col1, col2 = st.columns(2, gap="small")

    with col1:
        st.download_button(
            label="Baixar Excel",
            data=gerar_excel(st.session_state.registros),
            file_name=f"{responsavel}_{medicao_fiscal}_{datetime.now().strftime('%d-%m-%Y')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )

    with col2:
        st.download_button(
            label="Baixar PDF",
            data=gerar_pdf(st.session_state.registros),
            file_name=f"{responsavel}_{medicao_fiscal}_{datetime.now().strftime('%d-%m-%Y')}.pdf",
            mime="application/pdf",
            use_container_width=True
        )

    if st.button(
        "Limpar Relatório",
        use_container_width=True
    ):
        st.session_state.registros = []
        # Limpa localStorage também
        st.components.v1.html(
            """
            <script>
            localStorage.removeItem("registros_gambiarra");
            </script>
            """,
            height=0
        )
        st.rerun()

# =====================================================
# FOOTER
# =====================================================

st.divider()
st.caption("Desenvolvido por José Pedrosa")
