import streamlit as st
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
from datetime import datetime
import pandas as pd
import tempfile
import os
import json
import base64
from pathlib import Path

# PDF
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Image as RLImage,
    PageBreak,
    Table,
    TableStyle
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm

# GEOLOCATION
try:
    from streamlit_geolocation import streamlit_geolocation
    HAS_GEOLOCATION = True
except:
    HAS_GEOLOCATION = False

# ==========================================
# CONFIG
# ==========================================

st.set_page_config(
    page_title="Relatório Fotográfico Inteligente",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS CUSTOMIZADO
st.markdown("""
<style>
    .stMetric {
        background-color: #f0f2f6;
        padding: 15px;
        border-radius: 10px;
    }
    .photo-card {
        border: 2px solid #e0e0e0;
        border-radius: 10px;
        padding: 15px;
        margin: 10px 0;
    }
    .success-box {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
        padding: 15px;
        border-radius: 5px;
    }
</style>
""", unsafe_allow_html=True)

st.title("📍 Relatório Fotográfico Inteligente")

# ==========================================
# SESSION STATE
# ==========================================

if "registros" not in st.session_state:
    st.session_state.registros = []

if "filtro_tag" not in st.session_state:
    st.session_state.filtro_tag = "Todos"

if "modo_visualizacao" not in st.session_state:
    st.session_state.modo_visualizacao = "Grade"

# ==========================================
# SIDEBAR - CONFIGURAÇÕES
# ==========================================

with st.sidebar:
    st.header("⚙️ Configurações")
    
    modo_captura = st.radio(
        "📷 Modo de Captura",
        ["Câmera", "Upload de Arquivo", "Webcam em Tempo Real"]
    )
    
    st.divider()
    
    # Estatísticas
    st.subheader("📊 Estatísticas")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Total de Fotos", len(st.session_state.registros))
    with col2:
        fotos_com_gps = sum(1 for r in st.session_state.registros if r.get("latitude"))
        st.metric("Com GPS", fotos_com_gps)
    
    st.divider()
    
    # Tags
    st.subheader("🏷️ Filtrar por Tag")
    todas_tags = set()
    for reg in st.session_state.registros:
        todas_tags.update(reg.get("tags", []))
    
    tags_filtro = ["Todos"] + sorted(list(todas_tags))
    st.session_state.filtro_tag = st.selectbox(
        "Selecione uma tag",
        tags_filtro
    )
    
    st.divider()
    
    # Modo de visualização
    st.subheader("👁️ Visualização")
    st.session_state.modo_visualizacao = st.radio(
        "Modo",
        ["Grade", "Lista", "Mapa"]
    )
    
    st.divider()
    
    # Limpar dados
    if st.button("🗑️ Limpar Todos os Dados", type="secondary"):
        st.session_state.registros = []
        st.success("Dados limpos!")
        st.rerun()

# ==========================================
# CAPTURA - CÂMERA
# ==========================================

if modo_captura == "Câmera":
    st.subheader("📸 Captura via Câmera")
    
    col_cam, col_geo = st.columns([2, 1])
    
    with col_cam:
        foto = st.camera_input("Tire uma foto")
    
    with col_geo:
        st.subheader("📡 Localização")
        if HAS_GEOLOCATION:
            location = streamlit_geolocation()
            
            if location:
                latitude = location["latitude"]
                longitude = location["longitude"]
                st.success(f"✅ Localização capturada!")
                st.write(f"Lat: {latitude:.4f}")
                st.write(f"Lon: {longitude:.4f}")
            else:
                latitude = None
                longitude = None
                st.warning("Permita acesso à localização")
        else:
            st.info("Geolocalização não disponível")
            latitude = None
            longitude = None

# ==========================================
# CAPTURA - UPLOAD
# ==========================================

elif modo_captura == "Upload de Arquivo":
    st.subheader("📁 Upload de Arquivo")
    
    col_upload, col_geo = st.columns([2, 1])
    
    with col_upload:
        foto = st.file_uploader(
            "Selecione uma foto",
            type=["jpg", "jpeg", "png", "webp"]
        )
    
    with col_geo:
        st.subheader("📡 Localização Manual")
        latitude = st.number_input("Latitude", value=0.0, format="%.6f")
        longitude = st.number_input("Longitude", value=0.0, format="%.6f")
        
        usar_gps = st.checkbox("Usar coordenadas?")
        if not usar_gps:
            latitude = None
            longitude = None

# ==========================================
# CAPTURA - WEBCAM
# ==========================================

else:
    st.subheader("🎥 Webcam em Tempo Real")
    st.info("💡 Dica: Tire múltiplas fotos da mesma posição para ter mais opções")
    
    foto = st.camera_input("Webcam ao vivo")
    
    # Geolocalização para webcam
    latitude = None
    longitude = None
    if HAS_GEOLOCATION:
        location = streamlit_geolocation()
        if location:
            latitude = location["latitude"]
            longitude = location["longitude"]

# ==========================================
# PROCESSAMENTO DA FOTO
# ==========================================

if foto:
    imagem = Image.open(foto)
    
    st.subheader("🖼️ Pré-visualização e Detalhes")
    
    col_img, col_info = st.columns([2, 1])
    
    with col_img:
        st.image(imagem, use_container_width=True)
    
    with col_info:
        st.write("**Informações da Foto:**")
        st.write(f"Tamanho: {imagem.size[0]}x{imagem.size[1]}px")
        st.write(f"Formato: {imagem.format}")
        
        # Informações EXIF se disponíveis
        try:
            exif_data = imagem._getexif()
            if exif_data:
                st.write("✅ EXIF disponível")
        except:
            st.write("ℹ️ Sem dados EXIF")
    
    # FORMULÁRIO DE DETALHES
    st.divider()
    st.subheader("✍️ Detalhes do Apontamento")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        nome_apontamento = st.text_input(
            "Nome do Apontamento",
            value=f"Apontamento {len(st.session_state.registros)+1}"
        )
    
    with col2:
        categorias = ["Inspeção", "Reparo", "Manutenção", "Documentação", "Outro"]
        categoria = st.selectbox("Categoria", categorias)
    
    with col3:
        prioridade = st.selectbox("Prioridade", ["Baixa", "Média", "Alta"])
    
    # Tags
    tags_input = st.text_input(
        "Tags (separadas por vírgula)",
        placeholder="ex: urgente, área-externa, risco"
    )
    tags = [tag.strip() for tag in tags_input.split(",") if tag.strip()]
    
    # Descrição
    descricao = st.text_area(
        "Descrição adicional",
        placeholder="Adicione observações, problemas encontrados, etc...",
        height=100
    )
    
    # Assinatura
    st.subheader("✋ Responsável")
    responsavel = st.text_input("Nome do Responsável", placeholder="Seu nome")
    
    # ==========================================
    # CONFIRMAR FOTO
    # ==========================================
    
    col_btn1, col_btn2, col_btn3 = st.columns(3)
    
    with col_btn1:
        if st.button("✅ Adicionar Foto ao Relatório", type="primary"):
            
            if not responsavel.strip():
                st.error("❌ Por favor, insira o nome do responsável")
            else:
                data_hora = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
                
                nome_arquivo = (
                    f"{nome_apontamento.replace(' ', '_')}_"
                    f"{datetime.now().strftime('%d-%m-%Y_%H-%M-%S')}"
                )
                
                maps_link = None
                if latitude and longitude and latitude != 0.0 and longitude != 0.0:
                    maps_link = (
                        f"https://www.google.com/maps?q="
                        f"{latitude},{longitude}"
                    )
                
                registro = {
                    "id": len(st.session_state.registros),
                    "apontamento": nome_apontamento,
                    "nome_arquivo": nome_arquivo,
                    "imagem": imagem.copy(),
                    "latitude": latitude if latitude and latitude != 0.0 else None,
                    "longitude": longitude if longitude and longitude != 0.0 else None,
                    "maps_link": maps_link,
                    "data_hora": data_hora,
                    "categoria": categoria,
                    "prioridade": prioridade,
                    "tags": tags,
                    "descricao": descricao,
                    "responsavel": responsavel
                }
                
                st.session_state.registros.append(registro)
                st.success("✅ Foto adicionada ao relatório com sucesso!")
                st.rerun()
    
    with col_btn2:
        if st.button("🎯 Adicionar + Outra", type="secondary"):
            st.info("Câmera reiniciada. Tire outra foto!")
    
    with col_btn3:
        st.button("❌ Descartar", type="secondary")

# ==========================================
# VISUALIZAÇÃO DO RELATÓRIO
# ==========================================

if st.session_state.registros:
    
    st.divider()
    st.subheader("📑 Relatório de Apontamentos")
    
    # FILTRAR REGISTROS
    registros_filtrados = st.session_state.registros
    
    if st.session_state.filtro_tag != "Todos":
        registros_filtrados = [
            r for r in registros_filtrados 
            if st.session_state.filtro_tag in r.get("tags", [])
        ]
    
    st.info(f"📌 Exibindo {len(registros_filtrados)} de {len(st.session_state.registros)} fotos")
    
    # ==========================================
    # VISUALIZAÇÃO EM GRADE
    # ==========================================
    
    if st.session_state.modo_visualizacao == "Grade":
        
        cols = st.columns(3)
        
        for idx, reg in enumerate(registros_filtrados):
            
            with cols[idx % 3]:
                st.markdown(f"""
                <div class='photo-card'>
                    <b>{reg['apontamento']}</b>
                </div>
                """, unsafe_allow_html=True)
                
                st.image(reg["imagem"], use_container_width=True)
                
                # Info compacta
                st.caption(f"🏷️ {', '.join(reg.get('tags', ['sem-tag']))}")
                st.caption(f"👤 {reg.get('responsavel', 'N/A')}")
                st.caption(f"📅 {reg['data_hora']}")
                
                if reg.get("latitude") and reg.get("longitude"):
                    st.caption(f"📍 {reg['latitude']:.4f}, {reg['longitude']:.4f}")
                
                col_edit, col_del = st.columns(2)
                with col_edit:
                    if st.button(f"✏️ Editar", key=f"edit_{idx}"):
                        st.session_state.edit_index = idx
                with col_del:
                    if st.button(f"🗑️", key=f"del_{idx}"):
                        st.session_state.registros.pop(idx)
                        st.rerun()
    
    # ==========================================
    # VISUALIZAÇÃO EM LISTA
    # ==========================================
    
    elif st.session_state.modo_visualizacao == "Lista":
        
        for idx, reg in enumerate(registros_filtrados):
            
            with st.expander(f"📸 {reg['apontamento']} - {reg['responsavel']}", expanded=False):
                
                col1, col2 = st.columns([1, 2])
                
                with col1:
                    st.image(reg["imagem"], use_container_width=True)
                
                with col2:
                    st.write(f"**Categoria:** {reg.get('categoria', 'N/A')}")
                    st.write(f"**Prioridade:** {reg.get('prioridade', 'N/A')} 🔴")
                    st.write(f"**Responsável:** {reg.get('responsavel', 'N/A')}")
                    st.write(f"**Data/Hora:** {reg['data_hora']}")
                    
                    if reg.get("tags"):
                        st.write(f"**Tags:** {', '.join(reg['tags'])}")
                    
                    if reg.get("descricao"):
                        st.write(f"**Descrição:** {reg['descricao']}")
                    
                    if reg.get("latitude") and reg.get("longitude"):
                        st.write(f"**Localização:** {reg['latitude']:.6f}, {reg['longitude']:.6f}")
                        st.markdown(f"[🌎 Abrir no Google Maps]({reg['maps_link']})")
                    else:
                        st.write("**Localização:** Sem coordenadas")
                    
                    col_edit, col_del = st.columns(2)
                    with col_edit:
                        st.button(f"✏️ Editar", key=f"list_edit_{idx}")
                    with col_del:
                        if st.button(f"🗑️ Remover", key=f"list_del_{idx}"):
                            st.session_state.registros.pop(idx)
                            st.rerun()
    
    # ==========================================
    # VISUALIZAÇÃO EM MAPA
    # ==========================================
    
    else:  # Mapa
        
        registros_com_gps = [
            r for r in registros_filtrados 
            if r.get("latitude") and r.get("longitude")
        ]
        
        if registros_com_gps:
            
            # Preparar dados para o mapa
            dados_mapa = pd.DataFrame([
                {
                    "latitude": r["latitude"],
                    "longitude": r["longitude"],
                    "nome": r["apontamento"],
                    "responsavel": r.get("responsavel", "N/A")
                }
                for r in registros_com_gps
            ])
            
            st.map(dados_mapa)
            
            st.subheader("📍 Apontamentos no Mapa")
            st.dataframe(dados_mapa, use_container_width=True)
        
        else:
            st.warning("⚠️ Nenhum apontamento com coordenadas GPS para exibir no mapa")

# ==========================================
# EXPORTAR RELATÓRIOS
# ==========================================

if st.session_state.registros:
    
    st.divider()
    st.subheader("📤 Exportar Relatórios")
    
    # ==========================================
    # GERAR EXCEL AVANÇADO
    # ==========================================
    
    def gerar_excel_avancado(registros):
        
        df = pd.DataFrame([
            {
                "ID": idx + 1,
                "Apontamento": r["apontamento"],
                "Categoria": r.get("categoria", ""),
                "Prioridade": r.get("prioridade", ""),
                "Responsável": r.get("responsavel", ""),
                "Tags": ", ".join(r.get("tags", [])),
                "Descrição": r.get("descricao", ""),
                "Latitude": r.get("latitude", ""),
                "Longitude": r.get("longitude", ""),
                "Data/Hora": r["data_hora"],
                "Google Maps": r.get("maps_link", "")
            }
            for idx, r in enumerate(registros)
        ])
        
        output = BytesIO()
        
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, sheet_name="Apontamentos", index=False)
            
            # Formatação
            worksheet = writer.sheets["Apontamentos"]
            worksheet.column_dimensions['A'].width = 5
            worksheet.column_dimensions['B'].width = 20
            worksheet.column_dimensions['C'].width = 15
            worksheet.column_dimensions['D'].width = 12
            worksheet.column_dimensions['E'].width = 15
            worksheet.column_dimensions['F'].width = 20
            worksheet.column_dimensions['G'].width = 25
        
        return output.getvalue()
    
    # ==========================================
    # GERAR PDF PROFISSIONAL
    # ==========================================
    
    def gerar_pdf_profissional(registros):
        
        buffer = BytesIO()
        
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=1*cm,
            leftMargin=1*cm,
            topMargin=1*cm,
            bottomMargin=1*cm
        )
        
        styles = getSampleStyleSheet()
        
        # Estilos customizados
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1f77b4'),
            spaceAfter=30,
            alignment=1
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#2ca02c'),
            spaceAfter=10,
            spaceBefore=10
        )
        
        elementos = []
        
        # Cabeçalho
        elementos.append(
            Paragraph(
                "📍 RELATÓRIO FOTOGRÁFICO INTELIGENTE",
                title_style
            )
        )
        
        data_relatorio = datetime.now().strftime("%d de %B de %Y às %H:%M")
        elementos.append(
            Paragraph(
                f"Gerado em: {data_relatorio}",
                styles["Normal"]
            )
        )
        
        elementos.append(Spacer(1, 20))
        
        # Sumário
        elementos.append(Paragraph("SUMÁRIO", heading_style))
        
        tabela_sumario = Table([
            ["Total de Apontamentos", str(len(registros))],
            ["Com Coordenadas GPS", str(sum(1 for r in registros if r.get("latitude")))],
            ["Data de Início", registros[0]["data_hora"] if registros else "N/A"],
            ["Data de Término", registros[-1]["data_hora"] if registros else "N/A"]
        ])
        
        tabela_sumario.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#e8f4f8')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        elementos.append(tabela_sumario)
        elementos.append(Spacer(1, 20))
        
        # Apontamentos
        for idx, reg in enumerate(registros, 1):
            
            elementos.append(PageBreak() if idx > 1 else Spacer(1, 10))
            
            elementos.append(
                Paragraph(
                    f"Apontamento {idx}: {reg['apontamento']}",
                    heading_style
                )
            )
            
            # Info tabular
            info_table = Table([
                ["Responsável", reg.get("responsavel", "N/A")],
                ["Categoria", reg.get("categoria", "N/A")],
                ["Prioridade", reg.get("prioridade", "N/A")],
                ["Data/Hora", reg["data_hora"]],
                ["Tags", ", ".join(reg.get("tags", ["N/A"]))],
                ["Latitude", f"{reg.get('latitude', 'N/A')}"],
                ["Longitude", f"{reg.get('longitude', 'N/A')}"]
            ])
            
            info_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f0f0f0')),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
                ('GRID', (0, 0), (-1, -1), 1, colors.lightgrey)
            ]))
            
            elementos.append(info_table)
            elementos.append(Spacer(1, 15))
            
            # Imagem
            with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
                caminho = tmp.name
                reg["imagem"].save(caminho, format="JPEG")
            
            img = RLImage(caminho, width=15*cm, height=11*cm)
            elementos.append(img)
            
            elementos.append(Spacer(1, 10))
            
            # Descrição
            if reg.get("descricao"):
                elementos.append(
                    Paragraph(
                        f"<b>Descrição:</b> {reg['descricao']}",
                        styles["Normal"]
                    )
                )
                elementos.append(Spacer(1, 10))
        
        doc.build(elementos)
        
        # Limpar arquivos temporários
        for arq in os.listdir(tempfile.gettempdir()):
            if arq.endswith(".jpg"):
                try:
                    os.remove(os.path.join(tempfile.gettempdir(), arq))
                except:
                    pass
        
        return buffer.getvalue()
    
    # ==========================================
    # BOTÕES DE DOWNLOAD
    # ==========================================
    
    col_down1, col_down2, col_down3 = st.columns(3)
    
    with col_down1:
        excel_bytes = gerar_excel_avancado(st.session_state.registros)
        st.download_button(
            label="📊 Baixar Excel",
            data=excel_bytes,
            file_name=f"relatorio_{datetime.now().strftime('%d-%m-%Y_%H-%M-%S')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    
    with col_down2:
        pdf_bytes = gerar_pdf_profissional(st.session_state.registros)
        st.download_button(
            label="📄 Baixar PDF Profissional",
            data=pdf_bytes,
            file_name=f"relatorio_{datetime.now().strftime('%d-%m-%Y_%H-%M-%S')}.pdf",
            mime="application/pdf"
        )
    
    with col_down3:
        # JSON backup
        json_data = json.dumps([
            {
                k: v if k != "imagem" else None 
                for k, v in reg.items()
            }
            for reg in st.session_state.registros
        ], indent=2, ensure_ascii=False)
        
        st.download_button(
            label="💾 Backup JSON",
            data=json_data,
            file_name=f"backup_{datetime.now().strftime('%d-%m-%Y_%H-%M-%S')}.json",
            mime="application/json"
        )

# ==========================================
# RODAPÉ
# ==========================================

st.divider()

col_foot1, col_foot2, col_foot3 = st.columns(3)

with col_foot1:
    st.caption("🚀 Versão 2.0 - Relatório Fotográfico Inteligente")

with col_foot2:
    st.caption("📌 Desenvolvido com Streamlit")

with col_foot3:
    st.caption("💡 Sempre guarde backups de seus dados!")
