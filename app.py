import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Control Módulos LED Colombia", layout="wide")
st.title("🎛️ Panel de Control - Mantenimiento Módulos LED")

@st.cache_data(ttl=60)
def cargar_inventario():
    sheet_id = "166rj5uykRRDzjRlcKDa3WCR_f6FeREpc"
    gid = "995802095"
    url_csv = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
    
    # 1. Cargar el CSV sin asumir encabezados en la fila 0
    df_raw = pd.read_csv(url_csv, header=None)
    
    # 2. Localizar exactamente la fila que contiene las columnas 'Código' y 'Zona'
    header_idx = None
    for idx, row in df_raw.iterrows():
        row_cells = [str(val).lower().strip() for val in row.values]
        has_cod = any('cód' in cell or 'cod' in cell for cell in row_cells)
        has_zona = any('zona' in cell or 'regi' in cell for cell in row_cells)
        if has_cod and has_zona:
            header_idx = idx
            break
            
    if header_idx is not None:
        headers = [str(val).strip() for val in df_raw.iloc[header_idx].values]
        df = df_raw.iloc[header_idx + 1:].copy().reset_index(drop=True)
        df.columns = headers
    else:
        df = pd.read_csv(url_csv)
        df.columns = [str(c).strip() for c in df.columns]

    # 3. Mapear columnas de forma precisa
    col_codigo = next((c for c in df.columns if 'cód' in c.lower() or 'cod' in c.lower()), None)
    col_zona = next((c for c in df.columns if 'zona' in c.lower()), None)
    if not col_zona:
        col_zona = next((c for c in df.columns if 'regi' in c.lower()), None)
        
    col_marca = next((c for c in df.columns if 'marca' in c.lower()), None)
    col_ubicacion = next((c for c in df.columns if 'ubic' in c.lower() or 'pantalla' in c.lower()), None)
    
    # 4. Limpieza de filas vacías o inválidas
    if col_codigo:
        df = df[df[col_codigo].notna()]
        df = df[~df[col_codigo].astype(str).str.lower().isin(['nan', '', 'none', 'null', 'código', 'codigo'])]
        df[col_codigo] = df[col_codigo].astype(str).str.replace('.0', '', regex=False).str.strip()
        
    return df, col_codigo, col_zona, col_marca, col_ubicacion

try:
    df_modulos, col_codigo, col_zona, col_marca, col_ubicacion = cargar_inventario()
    st.success("✅ Inventario cargado exitosamente")
except Exception as e:
    st.error("❌ Ocurrió un error al cargar la hoja de cálculo:")
    st.exception(e)
    st.stop()

# ----------------------------------------------------
# FILTROS Y SEGMENTACIÓN POR ZONA
# ----------------------------------------------------
st.header("📋 Inventario y Segmentación por Zona")

col1, col2, col3 = st.columns(3)

with col1:
    if col_zona and col_zona in df_modulos.columns:
        # Obtener zonas únicas reales (ej. CENTRO, BOGOTA, PACIFICO, etc.)
        zonas_unicas = sorted([
            z for z in df_modulos[col_zona].astype(str).str.strip().unique() 
            if z.lower() not in ['nan', '', 'none', 'null', 'zona', 'región', 'region']
        ])
        zona_sel = st.multiselect("Filtrar por Zona", options=zonas_unicas, help="Selecciona una o varias zonas para segmentar los códigos.")
    else:
        st.warning("Columna 'Zona' no identificada")
        zona_sel = []

with col2:
    if col_marca and col_marca in df_modulos.columns:
        marcas_unicas = sorted([
            m for m in df_modulos[col_marca].astype(str).str.strip().unique() 
            if m.lower() not in ['nan', '', 'none', 'null', 'marca']
        ])
        marca_sel = st.multiselect("Filtrar por Marca", options=marcas_unicas)
    else:
        marca_sel = []

with col3:
    if col_ubicacion and col_ubicacion in df_modulos.columns:
        ubic_unicas = sorted([
            u for u in df_modulos[col_ubicacion].astype(str).str.strip().unique() 
            if u.lower() not in ['nan', '', 'none', 'null', 'ubicacion actual', 'ubicación actual']
        ])
        ubicacion_sel = st.multiselect("Filtrar por Ubicación", options=ubic_unicas)
    else:
        ubicacion_sel = []

# Aplicación del filtrado reactivo
df_filtrado = df_modulos.copy()

if zona_sel and col_zona:
    df_filtrado = df_filtrado[df_filtrado[col_zona].astype(str).str.strip().isin(zona_sel)]

if marca_sel and col_marca:
    df_filtrado = df_filtrado[df_filtrado[col_marca].astype(str).str.strip().isin(marca_sel)]

if ubicacion_sel and col_ubicacion:
    df_filtrado = df_filtrado[df_filtrado[col_ubicacion].astype(str).str.strip().isin(ubicacion_sel)]

# Mostrar la tabla segmentada
st.dataframe(df_filtrado, use_container_width=True, hide_index=True)

# ----------------------------------------------------
# PROGRAMACIÓN DE JORNADAS (CÓDIGOS SEGMENTADOS)
# ----------------------------------------------------
st.header("🛠️ Programar / Registrar Jornada")

# Mensaje contextual según la zona seleccionada
if zona_sel:
    st.info(f"📌 **Zona(s) seleccionada(s):** {', '.join(zona_sel)} — Mostrando **{len(df_filtrado)}** módulo(s) disponible(s).")
else:
    st.caption("💡 Tip: Selecciona una Zona en los filtros superiores para ver únicamente los códigos de esa área.")

with st.form("form_jornada"):
    col_a, col_b = st.columns(2)
    
    with col_a:
        # Los códigos disponibles se generan DENTRO de df_filtrado (según la zona elegida)
        codigos_disponibles = sorted(df_filtrado[col_codigo].unique().tolist()) if col_codigo else []
        codigos_jornada = st.multiselect(
            f"Seleccionar Módulos ({len(codigos_disponibles)} disponibles en el filtro)", 
            options=codigos_disponibles
        )
        
        tipo_jornada = st.selectbox("Tipo de Jornada", [
            "Mantenimiento Preventivo", 
            "Conteo de LED Fallidos", 
            "Mantenimiento Correctivo", 
            "Limpieza / Ajuste / Calibración"
        ])
    
    with col_b:
        fecha_jornada = st.date_input("Fecha de la Jornada", datetime.today())
        tecnico = st.text_input("Técnico Asignado")
        observaciones = st.text_area("Observaciones")
        
    submit = st.form_submit_button("Registrar Jornada")
    
    if submit:
        if not codigos_jornada:
            st.warning("Selecciona al menos un código de módulo.")
        else:
            bimestre_num = (fecha_jornada.month - 1) // 2 + 1
            bimestre_id = f"{fecha_jornada.year}-B{bimestre_num}"
            
            st.success(f"✅ Jornada '{tipo_jornada}' registrada para {len(codigos_jornada)} módulo(s) en el período **{bimestre_id}**.")
            
            resumen = pd.DataFrame({
                "Bimestre": [bimestre_id] * len(codigos_jornada),
                "Fecha": [fecha_jornada] * len(codigos_jornada),
                "Código Módulo": codigos_jornada,
                "Tipo Jornada": [tipo_jornada] * len(codigos_jornada),
                "Técnico": [tecnico] * len(codigos_jornada),
                "Observaciones": [observaciones] * len(codigos_jornada)
            })
            st.dataframe(resumen, hide_index=True)
