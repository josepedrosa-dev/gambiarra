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
    .gps-box-success {
        background-color: #d4edda;
        border-left: 4px solid #28a745;
        padding: 15px;
        border-radius: 5px;
        margin: 10px 0;
    }
    .gps-box-warning {
        background-color: #fff3cd;
        border-left: 4px solid #ffc107;
        padding: 15px;
        border-radius: 5px;
        margin: 10px 0;
    }
    .gps-box-error {
        background-color: #f8d7da;
        border-left: 4px solid #dc3545;
        padding: 15px;
        border-radius: 5px;
        margin: 10px 0;
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

if "gps_manual" not in st.session_state:
    st.session_state.gps_manual = {"lat": None, "lon": None, "source": None}

if "foto_atual" not in st.session_state:
    st.session_state.foto_atual = None

# ==========================================
# FUNÇÃO: CAPTURAR GPS VIA JAVASCRIPT
# ==========================================

def capturar_gps_html():
    """Captura GPS usando HTML5 Geolocation API"""
    gps_html = """
    <div id="gps-container" style="padding: 10px; border: 1px solid #ddd; border-radius: 5px; margin: 10px 0;">
        <button id="gps-btn" onclick="captureGPS()" style="
            padding: 10px 20px;
            background-color: #1976d2;
            color: white;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-size: 14px;
            font-weight: bold;
        ">🌍 Capturar GPS Agora</button>
        <div id="gps-status" style="margin-top: 10px; display: none;"></div>
    </div>
    
    <script>
    function captureGPS() {
        const btn = document.getElementById('gps-btn');
        const status = document.getElementById('gps-status');
        
        btn.disabled = true;
        btn.textContent = '⏳ Capturando...';
        status.style.display = 'block';
        status.innerHTML = '<p style="color: #1976d2;">Solicitando acesso ao GPS do seu dispositivo...</p>';
        
        if (!navigator.geolocation) {
            status.innerHTML = '<p style="color: #dc3545;">❌ Geolocalização não suportada pelo navegador</p>';
            btn.disabled = false;
            btn.textContent = '🌍 Capturar GPS Novamente';
            return;
        }
        
        const options = {
            enableHighAccuracy: true,
            timeout: 30000,
            maximumAge: 0
        };
        
        navigator.geolocation.getCurrentPosition(
            function(position) {
                const lat = position.coords.latitude.toFixed(8);
                const lon = position.coords.longitude.toFixed(8);
                const acc = position.coords.accuracy.toFixed(2);
                
                status.innerHTML = `
                    <div style="background-color: #d4edda; border: 1px solid #c3e6cb; padding: 10px; border-radius: 5px;">
                        <p style="color: #155724; margin: 0;"><strong>✅ GPS Capturado com Sucesso!</strong></p>
                        <p style="color: #155724; margin: 5px 0;">Latitude: ${lat}°</p>
                        <p style="color: #155724; margin: 5px 0;">Longitude: ${lon}°</p>
                        <p style="color: #155724; margin: 5px 0;">Precisão: ±${acc} metros</p>
                    </div>
                `;
                
                // Enviar dados para Streamlit
                window.parent.postMessage({
                    type: 'streamlit:setComponentValue',
                    value: {
                        latitude: parseFloat(lat),
                        longitude: parseFloat(lon),
                        accuracy: parseFloat(acc),
                        timestamp: new Date().toISOString(),
                        source: 'gps_html5'
                    }
                }, '*');
                
                btn.textContent = '✅ GPS Capturado';
                btn.style.backgroundColor = '#28a745';
            },
            function(error) {
                let errorMsg = '';
                
                if (error.code === error.PERMISSION_DENIED) {
                    errorMsg = '❌ Permissão negada. Verifique as configurações de privacidade do navegador.';
                } else if (error.code === error.POSITION_UNAVAILABLE) {
                    errorMsg = '⚠️ Informação de localização não disponível (você pode estar em local sem sinal).';
                } else if (error.code === error.TIMEOUT) {
                    errorMsg = '⏱️ Timeout ao capturar GPS. Tente novamente.';
                } else {
                    errorMsg = `❌ Erro: ${error.message}`;
                }
                
                status.innerHTML = `<p style="color: #dc3545;">${errorMsg}</p>`;
                btn.disabled = false;
                btn.textContent = '🔄 Tentar Novamente';
            }
        );
    }
    </script>
    """
    return gps_html

# ==========================================
# SIDEBAR - CONFIGURAÇÕES
# ==========================================

with st.sidebar:
    st.header("⚙️ Configurações")
    
    modo_captura = st.radio(
        "📷 Modo de Captura",
        ["📸 Câmera", "📁 Upload", "🗺️ Coordenadas Manuais"]
    )
    
    st.divider()
    
    # Estatísticas
    st.subheader("📊 Estatísticas")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total", len(st.session_state.registros))
    with col2:
        fotos_com_gps = sum(1 for r in st.session_state.registros if r.get("latitude"))
        st.metric("Com GPS", fotos_com_gps)
    with col3:
        st.metric("Sem GPS", len(st.session_state.registros) - fotos_com_gps)
    
    st.divider()
    
    # Tags
    st.subheader("🏷️ Filtrar por Tag")
    todas_tags = set()
    for reg in st.session_state.registros:
        todas_tags.update(reg.get("tags", []))
    
    tags_filtro = ["Todos"] + sorted(list(todas_tags))
    st.session_state.filtro_tag = st.selectbox(
        "Selecione uma tag",
        tags_filtro,
        key="filtro_tag_select"
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
        st.session_state.gps_manual = {"lat": None, "lon": None, "source": None}
        st.success("Dados limpos!")
        st.rerun()

# ==========================================
# MODO 1: CÂMERA
# ==========================================

if modo_captura == "📸 Câmera":
    
    st.subheader("📸 Captura via Câmera")
    st.info("💡 Você pode capturar GPS após tirar a foto, mas não é obrigatório para salvar o apontamento")
    
    col_cam, col_gps = st.columns([2, 1])
    
    with col_cam:
        foto = st.camera_input("Tire uma foto", key="camera_input")
    
    with col_gps:
        st.subheader("📡 GPS")
        
        # Exibir status do GPS
        if st.session_state.gps_manual["lat"] is not None:
            st.markdown(f"""
            <div class='gps-box-success'>
            <strong>✅ GPS Capturado!</strong><br>
            Lat: {st.session_state.gps_manual['lat']:.6f}°<br>
            Lon: {st.session_state.gps_manual['lon']:.6f}°<br>
            <small>Fonte: {st.session_state.gps_manual['source']}</small>
            </div>
            """, unsafe_allow_html=True)
            
            if st.button("🔄 Recapturar GPS"):
                st.session_state.gps_manual = {"lat": None, "lon": None, "source": None}
                st.rerun()
        else:
            st.markdown("""
            <div class='gps-box-warning'>
            <strong>⚠️ GPS não capturado</strong><br>
            Clique no botão abaixo para tentar capturar
            </div>
            """, unsafe_allow_html=True)
            
            st.components.v1.html(capturar_gps_html(), height=250)
    
    # PROCESSAMENTO DA FOTO
    if foto is not None:
        try:
            imagem = Image.open(foto)
            st.session_state.foto_atual = imagem.copy()
            
            st.subheader("🖼️ Pré-visualização")
            
            col_img, col_info = st.columns([2, 1])
            
            with col_img:
                st.image(imagem, use_container_width=True)
            
            with col_info:
                st.write("**Informações:**")
                try:
                    st.write(f"Tamanho: {imagem.size[0]}x{imagem.size[1]}px")
                    st.write(f"Formato: {imagem.format if imagem.format else 'Desconhecido'}")
                except Exception as e:
                    st.write(f"Erro: {str(e)}")
            
            # FORMULÁRIO DE DETALHES
            st.divider()
            st.subheader("✍️ Detalhes do Apontamento")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                nome_apontamento = st.text_input(
                    "Nome do Apontamento",
                    value=f"Apontamento {len(st.session_state.registros)+1}",
                    key="cam_nome"
                )
            
            with col2:
                categorias = ["Inspeção", "Reparo", "Manutenção", "Documentação", "Outro"]
                categoria = st.selectbox("Categoria", categorias, key="cam_cat")
            
            with col3:
                prioridade = st.selectbox("Prioridade", ["Baixa", "Média", "Alta"], key="cam_pri")
            
            # Tags
            tags_input = st.text_input(
                "Tags (separadas por vírgula)",
                placeholder="ex: urgente, área-externa",
                key="cam_tags"
            )
            tags = [tag.strip() for tag in tags_input.split(",") if tag.strip()]
            
            # Descrição
            descricao = st.text_area(
                "Descrição adicional",
                placeholder="Observações, problemas encontrados, etc...",
                height=100,
                key="cam_desc"
            )
            
            # Responsável
            st.subheader("✋ Responsável")
            responsavel = st.text_input("Nome do Responsável", placeholder="Seu nome", key="cam_resp")
            
            # ==========================================
            # CONFIRMAR E SALVAR
            # ==========================================
            
            col_btn1, col_btn2, col_btn3 = st.columns(3)
            
            with col_btn1:
                if st.button("✅ Salvar ao Relatório", type="primary", key="cam_save"):
                    
                    if not responsavel.strip():
                        st.error("❌ Por favor, insira o nome do responsável")
                    else:
                        try:
                            data_hora = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
                            
                            nome_arquivo = (
                                f"{nome_apontamento.replace(' ', '_')}_"
                                f"{datetime.now().strftime('%d-%m-%Y_%H-%M-%S')}"
                            )
                            
                            latitude = st.session_state.gps_manual["lat"]
                            longitude = st.session_state.gps_manual["lon"]
                            
                            maps_link = None
                            if latitude is not None and longitude is not None:
                                maps_link = f"https://www.google.com/maps?q={latitude},{longitude}"
                            
                            registro = {
                                "id": len(st.session_state.registros),
                                "apontamento": nome_apontamento,
                                "nome_arquivo": nome_arquivo,
                                "imagem": st.session_state.foto_atual.copy(),
                                "latitude": latitude,
                                "longitude": longitude,
                                "maps_link": maps_link,
                                "data_hora": data_hora,
                                "categoria": categoria,
                                "prioridade": prioridade,
                                "tags": tags,
                                "descricao": descricao,
                                "responsavel": responsavel,
                                "gps_source": st.session_state.gps_manual.get("source")
                            }
                            
                            st.session_state.registros.append(registro)
                            st.session_state.gps_manual = {"lat": None, "lon": None, "source": None}
                            st.session_state.foto_atual = None
                            
                            st.success("✅ Apontamento salvo com sucesso!")
                            st.balloons()
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Erro ao salvar: {str(e)}")
            
            with col_btn2:
                if st.button("🔄 Outra Foto", type="secondary", key="cam_other"):
                    st.session_state.gps_manual = {"lat": None, "lon": None, "source": None}
                    st.session_state.foto_atual = None
                    st.rerun()
            
            with col_btn3:
                if st.button("❌ Descartar", type="secondary", key="cam_discard"):
                    st.session_state.gps_manual = {"lat": None, "lon": None, "source": None}
                    st.session_state.foto_atual = None
                    st.rerun()
        
        except Exception as e:
            st.error(f"❌ Erro ao processar imagem: {str(e)}")

# ==========================================
# MODO 2: UPLOAD
# ==========================================

elif modo_captura == "📁 Upload":
    
    st.subheader("📁 Upload de Arquivo")
    
    col_upload, col_gps = st.columns([2, 1])
    
    with col_upload:
        foto = st.file_uploader(
            "Selecione uma foto",
            type=["jpg", "jpeg", "png", "webp"],
            key="upload_input"
        )
    
    with col_gps:
        st.subheader("📡 GPS")
        
        if st.session_state.gps_manual["lat"] is not None:
            st.markdown(f"""
            <div class='gps-box-success'>
            <strong>✅ GPS Definido!</strong><br>
            Lat: {st.session_state.gps_manual['lat']:.6f}°<br>
            Lon: {st.session_state.gps_manual['lon']:.6f}°<br>
            <small>Fonte: {st.session_state.gps_manual['source']}</small>
            </div>
            """, unsafe_allow_html=True)
            
            if st.button("🔄 Alterar GPS"):
                st.session_state.gps_manual = {"lat": None, "lon": None, "source": None}
                st.rerun()
        else:
            st.markdown("""
            <div class='gps-box-warning'>
            <strong>⚠️ GPS não definido</strong><br>
            Clique para capturar ou insira manualmente
            </div>
            """, unsafe_allow_html=True)
            
            st.components.v1.html(capturar_gps_html(), height=200)
    
    if foto is not None:
        try:
            imagem = Image.open(foto)
            st.session_state.foto_atual = imagem.copy()
            
            st.subheader("🖼️ Pré-visualização")
            st.image(imagem, use_container_width=True)
            
            # FORMULÁRIO
            st.divider()
            st.subheader("✍️ Detalhes")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                nome_apontamento = st.text_input(
                    "Apontamento",
                    value=f"Apontamento {len(st.session_state.registros)+1}",
                    key="upl_nome"
                )
            
            with col2:
                categoria = st.selectbox("Categoria", 
                    ["Inspeção", "Reparo", "Manutenção", "Documentação", "Outro"],
                    key="upl_cat"
                )
            
            with col3:
                prioridade = st.selectbox("Prioridade", ["Baixa", "Média", "Alta"], key="upl_pri")
            
            tags_input = st.text_input("Tags", key="upl_tags")
            tags = [tag.strip() for tag in tags_input.split(",") if tag.strip()]
            
            descricao = st.text_area("Descrição", height=100, key="upl_desc")
            responsavel = st.text_input("Responsável", key="upl_resp")
            
            if st.button("✅ Salvar Apontamento", type="primary", key="upl_save"):
                if not responsavel.strip():
                    st.error("❌ Insira o responsável")
                else:
                    try:
                        data_hora = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
                        
                        latitude = st.session_state.gps_manual["lat"]
                        longitude = st.session_state.gps_manual["lon"]
                        
                        maps_link = None
                        if latitude is not None and longitude is not None:
                            maps_link = f"https://www.google.com/maps?q={latitude},{longitude}"
                        
                        registro = {
                            "id": len(st.session_state.registros),
                            "apontamento": nome_apontamento,
                            "nome_arquivo": f"{nome_apontamento}_{data_hora}".replace(" ", "_").replace(":", "-"),
                            "imagem": st.session_state.foto_atual.copy(),
                            "latitude": latitude,
                            "longitude": longitude,
                            "maps_link": maps_link,
                            "data_hora": data_hora,
                            "categoria": categoria,
                            "prioridade": prioridade,
                            "tags": tags,
                            "descricao": descricao,
                            "responsavel": responsavel,
                            "gps_source": st.session_state.gps_manual.get("source")
                        }
                        
                        st.session_state.registros.append(registro)
                        st.session_state.gps_manual = {"lat": None, "lon": None, "source": None}
                        st.session_state.foto_atual = None
                        
                        st.success("✅ Salvo!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Erro: {str(e)}")
        
        except Exception as e:
            st.error(f"❌ Erro: {str(e)}")

# ==========================================
# MODO 3: COORDENADAS MANUAIS
# ==========================================

else:
    
    st.subheader("🗺️ Inserir Coordenadas Manualmente")
    
    col_coords, col_info = st.columns([2, 1])
    
    with col_coords:
        st.write("**Digite as coordenadas:**")
        col_lat, col_lon = st.columns(2)
        
        with col_lat:
            latitude = st.number_input(
                "Latitude",
                value=st.session_state.gps_manual["lat"] if st.session_state.gps_manual["lat"] else 0.0,
                format="%.8f",
                key="manual_lat"
            )
        
        with col_lon:
            longitude = st.number_input(
                "Longitude",
                value=st.session_state.gps_manual["lon"] if st.session_state.gps_manual["lon"] else 0.0,
                format="%.8f",
                key="manual_lon"
            )
        
        if st.button("✅ Confirmar Coordenadas"):
            st.session_state.gps_manual = {
                "lat": latitude if latitude != 0.0 else None,
                "lon": longitude if longitude != 0.0 else None,
                "source": "Entrada Manual"
            }
            st.success("✅ Coordenadas definidas!")
    
    with col_info:
        if st.session_state.gps_manual["lat"] is not None:
            st.markdown(f"""
            <div class='gps-box-success'>
            ✅ Coordenadas Confirmadas<br>
            {st.session_state.gps_manual['lat']:.6f}°<br>
            {st.session_state.gps_manual['lon']:.6f}°
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class='gps-box-warning'>
            ⚠️ Aguardando coordenadas
            </div>
            """, unsafe_allow_html=True)
    
    st.divider()
    
    # Upload da foto
    st.subheader("📸 Foto")
    foto = st.file_uploader("Selecione uma foto", type=["jpg", "jpeg", "png", "webp"], key="manual_upload")
    
    if foto:
        imagem = Image.open(foto)
        st.image(imagem, use_container_width=True)
        
        st.divider()
        
        # Formulário
        st.subheader("✍️ Detalhes")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            nome = st.text_input("Apontamento", key="man_nome")
        with col2:
            categoria = st.selectbox("Categoria", ["Inspeção", "Reparo", "Manutenção", "Documentação", "Outro"], key="man_cat")
        with col3:
            prioridade = st.selectbox("Prioridade", ["Baixa", "Média", "Alta"], key="man_pri")
        
        tags_input = st.text_input("Tags", key="man_tags")
        tags = [t.strip() for t in tags_input.split(",") if t.strip()]
        
        descricao = st.text_area("Descrição", height=100, key="man_desc")
        responsavel = st.text_input("Responsável", key="man_resp")
        
        if st.button("✅ Salvar", type="primary", key="man_save"):
            if not responsavel:
                st.error("Insira o responsável")
            else:
                try:
                    data_hora = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
                    
                    lat = st.session_state.gps_manual["lat"]
                    lon = st.session_state.gps_manual["lon"]
                    
                    maps_link = f"https://www.google.com/maps?q={lat},{lon}" if lat and lon else None
                    
                    registro = {
                        "id": len(st.session_state.registros),
                        "apontamento": nome,
                        "nome_arquivo": f"{nome}_{data_hora}".replace(" ", "_").replace(":", "-"),
                        "imagem": imagem.copy(),
                        "latitude": lat,
                        "longitude": lon,
                        "maps_link": maps_link,
                        "data_hora": data_hora,
                        "categoria": categoria,
                        "prioridade": prioridade,
                        "tags": tags,
                        "descricao": descricao,
                        "responsavel": responsavel,
                        "gps_source": "Entrada Manual"
                    }
                    
                    st.session_state.registros.append(registro)
                    st.session_state.gps_manual = {"lat": None, "lon": None, "source": None}
                    st.success("✅ Salvo!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro: {str(e)}")

# ==========================================
# VISUALIZAÇÃO DO RELATÓRIO
# ==========================================

if st.session_state.registros:
    
    st.divider()
    st.subheader("📑 Relatório")
    
    registros_filtrados = st.session_state.registros
    
    if st.session_state.filtro_tag != "Todos":
        registros_filtrados = [
            r for r in registros_filtrados 
            if st.session_state.filtro_tag in r.get("tags", [])
        ]
    
    st.info(f"📌 {len(registros_filtrados)}/{len(st.session_state.registros)} apontamentos")
    
    # GRADE
    if st.session_state.modo_visualizacao == "Grade":
        cols = st.columns(3)
        
        for idx, reg in enumerate(registros_filtrados):
            with cols[idx % 3]:
                st.markdown(f"**{reg['apontamento']}**")
                try:
                    st.image(reg["imagem"], use_container_width=True)
                except:
                    st.write("Imagem não disponível")
                
                st.caption(f"👤 {reg.get('responsavel', 'N/A')}")
                st.caption(f"📅 {reg['data_hora']}")
                st.caption(f"🏷️ {reg.get('categoria', 'N/A')}")
                
                if reg.get("latitude"):
                    st.caption(f"✅ 📍 GPS: {reg['latitude']:.4f}°, {reg['longitude']:.4f}°")
                else:
                    st.caption(f"❌ Sem GPS")
                
                col_a, col_b = st.columns(2)
                with col_a:
                    if st.button("📍 Mapa", key=f"map_{idx}"):
                        if reg.get("latitude"):
                            st.write(f"[Abrir no Maps]({reg['maps_link']})")
                        else:
                            st.write("Sem GPS")
                with col_b:
                    if st.button("🗑️", key=f"del_{idx}"):
                        st.session_state.registros.pop(idx)
                        st.rerun()
    
    # LISTA
    elif st.session_state.modo_visualizacao == "Lista":
        for idx, reg in enumerate(registros_filtrados):
            with st.expander(f"📸 {reg['apontamento']} - {reg.get('responsavel', 'N/A')}"):
                col1, col2 = st.columns([1, 2])
                
                with col1:
                    try:
                        st.image(reg["imagem"], use_container_width=True)
                    except:
                        st.write("Imagem não disponível")
                
                with col2:
                    st.write(f"**Categoria:** {reg.get('categoria', 'N/A')}")
                    st.write(f"**Prioridade:** {reg.get('prioridade', 'N/A')}")
                    st.write(f"**Data:** {reg['data_hora']}")
                    
                    if reg.get("latitude"):
                        st.write(f"**GPS:** {reg['latitude']:.8f}°, {reg['longitude']:.8f}°")
                        st.write(f"**Fonte:** {reg.get('gps_source', 'Desconhecida')}")
                        st.markdown(f"[🌎 Google Maps]({reg['maps_link']})")
                    else:
                        st.write("**GPS:** Não capturado")
                    
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
                st.error(f"Erro: {str(e)}")
        else:
            st.warning("Nenhum apontamento com GPS")

# ==========================================
# EXPORTAR
# ==========================================

if st.session_state.registros:
    st.divider()
    st.subheader("📤 Exportar")
    
    col1, col2 = st.columns(2)
    
    with col1:
        try:
            df = pd.DataFrame([
                {
                    "ID": r["id"] + 1,
                    "Apontamento": r["apontamento"],
                    "Categoria": r.get("categoria", ""),
                    "Prioridade": r.get("prioridade", ""),
                    "Responsável": r.get("responsavel", ""),
                    "Latitude": r.get("latitude", ""),
                    "Longitude": r.get("longitude", ""),
                    "GPS_Fonte": r.get("gps_source", ""),
                    "Data": r["data_hora"],
                    "Tags": ", ".join(r.get("tags", []))
                }
                for r in st.session_state.registros
            ])
            
            output = BytesIO()
            with pd.ExcelWriter(output, engine="openpyxl") as writer:
                df.to_excel(writer, sheet_name="Apontamentos", index=False)
            
            st.download_button(
                label="📊 Baixar Excel",
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

# Footer
st.divider()
st.caption("🚀 v3.0 | 📌 Desenvolvido com Streamlit | 💡 GPS capturado no navegador do dispositivo")
