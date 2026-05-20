import streamlit as st
from PIL import Image
from io import BytesIO
from datetime import datetime
import pandas as pd
import tempfile
import os
import json
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

# JavaScript Execution
try:
    from streamlit_js_eval import streamlit_js_eval
    HAS_JS_EVAL = True
except ImportError:
    HAS_JS_EVAL = False

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
    .gps-box {
        background-color: #e3f2fd;
        border-left: 4px solid #1976d2;
        padding: 15px;
        border-radius: 5px;
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

if "gps_capturado" not in st.session_state:
    st.session_state.gps_capturado = None

if "foto_atual" not in st.session_state:
    st.session_state.foto_atual = None

# ==========================================
# FUNÇÃO: CAPTURAR GPS COM JAVASCRIPT
# ==========================================

def capturar_gps_js():
    """Captura GPS usando JavaScript no navegador"""
    if not HAS_JS_EVAL:
        return None
    
    try:
        js_code = """
        new Promise((resolve) => {
            if (!navigator.geolocation) {
                resolve({error: "Geolocalização não suportada"});
            } else {
                navigator.geolocation.getCurrentPosition(
                    (position) => {
                        resolve({
                            latitude: position.coords.latitude,
                            longitude: position.coords.longitude,
                            accuracy: position.coords.accuracy,
                            timestamp: new Date().toISOString()
                        });
                    },
                    (error) => {
                        resolve({error: error.message});
                    },
                    {timeout: 10000, maximumAge: 0, enableHighAccuracy: true}
                );
            }
        });
        """
        resultado = streamlit_js_eval(js_string=js_code, want_output=True)
        return resultado
    except Exception as e:
        st.error(f"❌ Erro ao capturar GPS: {str(e)}")
        return None

# ==========================================
# SIDEBAR - CONFIGURAÇÕES
# ==========================================

with st.sidebar:
    st.header("⚙️ Configurações")
    
    modo_captura = st.radio(
        "📷 Modo de Captura",
        ["📸 Câmera + GPS", "📁 Upload Manual", "⚙️ Avançado"]
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
    
    # Informações
    with st.expander("ℹ️ Sobre GPS"):
        st.write("""
        **Captura de GPS:**
        - 🎯 Ativa apenas após tirar a foto
        - ⏱️ Aguarda confirmação do navegador
        - 🔄 Máx 10 segundos de espera
        - ✅ Coordenadas capturadas no momento exato
        """)
    
    st.divider()
    
    # Limpar dados
    if st.button("🗑️ Limpar Todos os Dados", type="secondary"):
        st.session_state.registros = []
        st.success("Dados limpos!")
        st.rerun()

# ==========================================
# MODO 1: CÂMERA + GPS INTELIGENTE
# ==========================================

if modo_captura == "📸 Câmera + GPS":
    
    st.subheader("📸 Captura via Câmera com GPS Automático")
    st.info("💡 A captura de GPS acontece após você tirar a foto para máxima precisão")
    
    col_cam, col_status = st.columns([2, 1])
    
    with col_cam:
        foto = st.camera_input("Tire uma foto")
    
    with col_status:
        st.subheader("📡 Status GPS")
        if st.session_state.gps_capturado:
            lat = st.session_state.gps_capturado.get("latitude")
            lon = st.session_state.gps_capturado.get("longitude")
            acc = st.session_state.gps_capturado.get("accuracy")
            
            if lat and lon:
                st.markdown(f"""
                <div class='gps-box'>
                <b>✅ Localização Capturada!</b><br>
                Lat: {lat:.6f}<br>
                Lon: {lon:.6f}<br>
                Precisão: ±{acc:.1f}m
                </div>
                """, unsafe_allow_html=True)
            else:
                st.error(f"❌ {st.session_state.gps_capturado.get('error', 'Erro desconhecido')}")
        else:
            st.warning("⏳ GPS não capturado ainda")
    
    # PROCESSAMENTO DA FOTO
    if foto is not None:
        try:
            imagem = Image.open(foto)
            st.session_state.foto_atual = imagem.copy()
            
            st.subheader("🖼️ Pré-visualização e Detalhes")
            
            col_img, col_info = st.columns([2, 1])
            
            with col_img:
                st.image(imagem, use_container_width=True)
            
            with col_info:
                st.write("**Informações da Foto:**")
                try:
                    st.write(f"🔍 Tamanho: {imagem.size[0]}x{imagem.size[1]}px")
                    st.write(f"📋 Formato: {imagem.format if imagem.format else 'Desconhecido'}")
                except Exception as e:
                    st.write(f"ℹ️ Erro: {str(e)}")
                
                # CAPTURAR GPS AGORA
                if st.button("🌍 Capturar GPS Agora", type="primary"):
                    with st.spinner("⏳ Solicitando acesso ao GPS..."):
                        gps_data = capturar_gps_js()
                        if gps_data and "latitude" in gps_data:
                            st.session_state.gps_capturado = gps_data
                            st.success("✅ GPS capturado com sucesso!")
                            st.rerun()
                        elif gps_data and "error" in gps_data:
                            st.error(f"❌ Erro: {gps_data['error']}")
                        else:
                            st.warning("⚠️ Não foi possível capturar GPS")
            
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
            
            # Responsável
            st.subheader("✋ Responsável")
            responsavel = st.text_input("Nome do Responsável", placeholder="Seu nome")
            
            # ==========================================
            # CONFIRMAR E SALVAR
            # ==========================================
            
            col_btn1, col_btn2, col_btn3 = st.columns(3)
            
            with col_btn1:
                if st.button("✅ Adicionar ao Relatório", type="primary"):
                    
                    if not responsavel.strip():
                        st.error("❌ Por favor, insira o nome do responsável")
                    elif not st.session_state.gps_capturado:
                        st.error("❌ Por favor, capture o GPS primeiro")
                    elif "error" in st.session_state.gps_capturado:
                        st.error(f"❌ GPS inválido: {st.session_state.gps_capturado['error']}")
                    else:
                        try:
                            data_hora = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
                            
                            nome_arquivo = (
                                f"{nome_apontamento.replace(' ', '_')}_"
                                f"{datetime.now().strftime('%d-%m-%Y_%H-%M-%S')}"
                            )
                            
                            latitude = st.session_state.gps_capturado.get("latitude")
                            longitude = st.session_state.gps_capturado.get("longitude")
                            accuracy = st.session_state.gps_capturado.get("accuracy", 0)
                            
                            maps_link = f"https://www.google.com/maps?q={latitude},{longitude}"
                            
                            registro = {
                                "id": len(st.session_state.registros),
                                "apontamento": nome_apontamento,
                                "nome_arquivo": nome_arquivo,
                                "imagem": st.session_state.foto_atual.copy(),
                                "latitude": latitude,
                                "longitude": longitude,
                                "accuracy": accuracy,
                                "maps_link": maps_link,
                                "data_hora": data_hora,
                                "categoria": categoria,
                                "prioridade": prioridade,
                                "tags": tags,
                                "descricao": descricao,
                                "responsavel": responsavel,
                                "gps_timestamp": st.session_state.gps_capturado.get("timestamp")
                            }
                            
                            st.session_state.registros.append(registro)
                            st.session_state.gps_capturado = None
                            st.session_state.foto_atual = None
                            
                            st.success("✅ Apontamento salvo com sucesso!")
                            st.balloons()
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Erro ao salvar: {str(e)}")
            
            with col_btn2:
                if st.button("🔄 Tirar Outra Foto", type="secondary"):
                    st.session_state.gps_capturado = None
                    st.session_state.foto_atual = None
                    st.info("📸 Câmera reiniciada")
                    st.rerun()
            
            with col_btn3:
                if st.button("❌ Descartar", type="secondary"):
                    st.session_state.gps_capturado = None
                    st.session_state.foto_atual = None
                    st.rerun()
        
        except Exception as e:
            st.error(f"❌ Erro ao processar imagem: {str(e)}")

# ==========================================
# MODO 2: UPLOAD MANUAL
# ==========================================

elif modo_captura == "📁 Upload Manual":
    
    st.subheader("📁 Upload Manual com GPS")
    
    col_upload, col_geo = st.columns([2, 1])
    
    with col_upload:
        foto = st.file_uploader(
            "Selecione uma foto",
            type=["jpg", "jpeg", "png", "webp"]
        )
    
    with col_geo:
        st.subheader("📡 Localização")
        entrada_gps = st.radio("Forma de entrada:", ["Manual", "Capturar GPS"])
        
        if entrada_gps == "Manual":
            latitude = st.number_input("Latitude", value=0.0, format="%.6f")
            longitude = st.number_input("Longitude", value=0.0, format="%.6f")
            usar_gps = latitude != 0.0 and longitude != 0.0
        else:
            if st.button("🌍 Capturar GPS do Navegador"):
                with st.spinner("⏳ Capturando GPS..."):
                    gps_data = capturar_gps_js()
                    if gps_data and "latitude" in gps_data:
                        latitude = gps_data["latitude"]
                        longitude = gps_data["longitude"]
                        st.success(f"✅ GPS: {latitude:.6f}, {longitude:.6f}")
                        usar_gps = True
                    else:
                        st.error("❌ Erro ao capturar GPS")
                        latitude = 0.0
                        longitude = 0.0
                        usar_gps = False
            else:
                latitude = 0.0
                longitude = 0.0
                usar_gps = False
    
    if foto and usar_gps if entrada_gps == "Manual" else True:
        try:
            imagem = Image.open(foto)
            
            st.subheader("🖼️ Pré-visualização")
            st.image(imagem, use_container_width=True)
            
            # FORMULÁRIO
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
            
            tags_input = st.text_input("Tags (separadas por vírgula)")
            tags = [tag.strip() for tag in tags_input.split(",") if tag.strip()]
            
            descricao = st.text_area("Descrição adicional", height=100)
            responsavel = st.text_input("Nome do Responsável")
            
            if st.button("✅ Salvar Apontamento", type="primary"):
                if not responsavel.strip():
                    st.error("❌ Insira o responsável")
                else:
                    try:
                        data_hora = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
                        nome_arquivo = (
                            f"{nome_apontamento.replace(' ', '_')}_"
                            f"{datetime.now().strftime('%d-%m-%Y_%H-%M-%S')}"
                        )
                        
                        if entrada_gps == "Manual":
                            lat_final = latitude if latitude != 0.0 else None
                            lon_final = longitude if longitude != 0.0 else None
                        else:
                            lat_final = latitude
                            lon_final = longitude
                        
                        maps_link = (
                            f"https://www.google.com/maps?q={lat_final},{lon_final}"
                            if lat_final and lon_final else None
                        )
                        
                        registro = {
                            "id": len(st.session_state.registros),
                            "apontamento": nome_apontamento,
                            "nome_arquivo": nome_arquivo,
                            "imagem": imagem.copy(),
                            "latitude": lat_final,
                            "longitude": lon_final,
                            "accuracy": None,
                            "maps_link": maps_link,
                            "data_hora": data_hora,
                            "categoria": categoria,
                            "prioridade": prioridade,
                            "tags": tags,
                            "descricao": descricao,
                            "responsavel": responsavel,
                            "gps_timestamp": None
                        }
                        
                        st.session_state.registros.append(registro)
                        st.success("✅ Apontamento salvo!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Erro: {str(e)}")
        
        except Exception as e:
            st.error(f"❌ Erro ao processar: {str(e)}")

# ==========================================
# MODO 3: AVANÇADO
# ==========================================

else:
    st.subheader("⚙️ Modo Avançado")
    
    tab1, tab2 = st.tabs(["📸 Câmera", "📁 Upload"])
    
    with tab1:
        st.write("Câmera com todas as opções")
        foto = st.camera_input("Câmera")
        
        if foto:
            imagem = Image.open(foto)
            st.image(imagem, use_container_width=True)
            
            col_gps, col_manual = st.columns(2)
            
            with col_gps:
                if st.button("🌍 Capturar GPS Automático"):
                    with st.spinner("⏳ Capturando..."):
                        gps_data = capturar_gps_js()
                        if gps_data and "latitude" in gps_data:
                            st.session_state.gps_capturado = gps_data
                            st.success("✅ GPS capturado!")
                        else:
                            st.error("❌ Erro ao capturar")
            
            with col_manual:
                if st.button("📍 Entrada Manual de GPS"):
                    st.session_state.gps_capturado = None
            
            # Rest of advanced form...
            nome_apontamento = st.text_input("Apontamento")
            categoria = st.selectbox("Categoria", ["Inspeção", "Reparo", "Manutenção", "Documentação", "Outro"])
            prioridade = st.selectbox("Prioridade", ["Baixa", "Média", "Alta"])
            tags_input = st.text_input("Tags")
            descricao = st.text_area("Descrição")
            responsavel = st.text_input("Responsável")
            
            if st.button("✅ Salvar"):
                if responsavel and st.session_state.gps_capturado:
                    tags = [tag.strip() for tag in tags_input.split(",") if tag.strip()]
                    data_hora = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
                    
                    gps = st.session_state.gps_capturado
                    lat = gps.get("latitude")
                    lon = gps.get("longitude")
                    
                    registro = {
                        "id": len(st.session_state.registros),
                        "apontamento": nome_apontamento,
                        "nome_arquivo": f"{nome_apontamento}_{data_hora}".replace(" ", "_").replace(":", "-"),
                        "imagem": imagem.copy(),
                        "latitude": lat,
                        "longitude": lon,
                        "accuracy": gps.get("accuracy"),
                        "maps_link": f"https://www.google.com/maps?q={lat},{lon}",
                        "data_hora": data_hora,
                        "categoria": categoria,
                        "prioridade": prioridade,
                        "tags": tags,
                        "descricao": descricao,
                        "responsavel": responsavel,
                        "gps_timestamp": gps.get("timestamp")
                    }
                    
                    st.session_state.registros.append(registro)
                    st.success("✅ Salvo!")
                    st.rerun()

# ==========================================
# VISUALIZAÇÃO DO RELATÓRIO
# ==========================================

if st.session_state.registros:
    
    st.divider()
    st.subheader("📑 Relatório de Apontamentos")
    
    # FILTRAR
    registros_filtrados = st.session_state.registros
    
    if st.session_state.filtro_tag != "Todos":
        registros_filtrados = [
            r for r in registros_filtrados 
            if st.session_state.filtro_tag in r.get("tags", [])
        ]
    
    st.info(f"📌 Exibindo {len(registros_filtrados)} de {len(st.session_state.registros)} fotos")
    
    # GRADE
    if st.session_state.modo_visualizacao == "Grade":
        cols = st.columns(3)
        
        for idx, reg in enumerate(registros_filtrados):
            with cols[idx % 3]:
                st.markdown(f"**{reg['apontamento']}**")
                try:
                    st.image(reg["imagem"], use_container_width=True)
                except:
                    pass
                
                st.caption(f"👤 {reg.get('responsavel', 'N/A')}")
                st.caption(f"📅 {reg['data_hora']}")
                
                if reg.get("latitude"):
                    st.caption(f"📍 {reg['latitude']:.4f}, {reg['longitude']:.4f}")
                    st.caption(f"±{reg.get('accuracy', 'N/A')}m")
                
                col_a, col_b = st.columns(2)
                with col_a:
                    if st.button("✏️", key=f"e{idx}"):
                        pass
                with col_b:
                    if st.button("🗑️", key=f"d{idx}"):
                        st.session_state.registros.pop(idx)
                        st.rerun()
    
    # LISTA
    elif st.session_state.modo_visualizacao == "Lista":
        for idx, reg in enumerate(registros_filtrados):
            with st.expander(f"📸 {reg['apontamento']} - {reg['responsavel']}"):
                col1, col2 = st.columns([1, 2])
                
                with col1:
                    try:
                        st.image(reg["imagem"], use_container_width=True)
                    except:
                        pass
                
                with col2:
                    st.write(f"**Categoria:** {reg.get('categoria', 'N/A')}")
                    st.write(f"**Prioridade:** {reg.get('prioridade', 'N/A')}")
                    st.write(f"**Data/Hora:** {reg['data_hora']}")
                    
                    if reg.get("latitude"):
                        st.write(f"**Localização:** {reg['latitude']:.6f}, {reg['longitude']:.6f}")
                        st.write(f"**Precisão GPS:** ±{reg.get('accuracy', 'N/A')}m")
                        st.markdown(f"[🌎 Google Maps]({reg['maps_link']})")
                    
                    if reg.get("descricao"):
                        st.write(f"**Descrição:** {reg['descricao']}")
                    
                    if st.button("🗑️ Remover", key=f"del_{idx}"):
                        st.session_state.registros.pop(idx)
                        st.rerun()
    
    # MAPA
    else:
        registros_com_gps = [r for r in registros_filtrados if r.get("latitude")]
        
        if registros_com_gps:
            try:
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
                st.dataframe(dados_mapa, use_container_width=True)
            except Exception as e:
                st.error(f"Erro ao exibir mapa: {str(e)}")
        else:
            st.warning("Sem apontamentos com GPS")

# ==========================================
# EXPORTAR
# ==========================================

if st.session_state.registros:
    st.divider()
    st.subheader("📤 Exportar")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        try:
            df = pd.DataFrame([
                {
                    "Apontamento": r["apontamento"],
                    "Categoria": r.get("categoria", ""),
                    "Responsável": r.get("responsavel", ""),
                    "Latitude": r.get("latitude", ""),
                    "Longitude": r.get("longitude", ""),
                    "Precisão (m)": r.get("accuracy", ""),
                    "Data/Hora": r["data_hora"]
                }
                for r in st.session_state.registros
            ])
            
            output = BytesIO()
            with pd.ExcelWriter(output, engine="openpyxl") as writer:
                df.to_excel(writer, sheet_name="Apontamentos", index=False)
            
            st.download_button(
                label="📊 Excel",
                data=output.getvalue(),
                file_name=f"relatorio_{datetime.now().strftime('%d-%m-%Y')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        except Exception as e:
            st.error(f"Erro: {str(e)}")
    
    with col2:
        try:
            json_data = json.dumps([
                {k: v if k != "imagem" else None for k, v in r.items()}
                for r in st.session_state.registros
            ], indent=2, ensure_ascii=False)
            
            st.download_button(
                label="💾 Backup JSON",
                data=json_data,
                file_name=f"backup_{datetime.now().strftime('%d-%m-%Y')}.json",
                mime="application/json"
            )
        except Exception as e:
            st.error(f"Erro: {str(e)}")
    
    with col3:
        if st.button("ℹ️ Info", type="secondary"):
            st.info(f"Total: {len(st.session_state.registros)} apontamentos")

# Footer
st.divider()
st.caption("🚀 v2.2 | 📌 Desenvolvido com Streamlit | 💡 GPS capturado no momento da foto")
