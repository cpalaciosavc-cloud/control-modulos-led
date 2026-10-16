import streamlit as st
import pandas as pd
from datetime import datetime
import requests
import io
import unicodedata

st.set_page_config(page_title="Control Módulos LED - Regiones y Zonas", layout="wide")
st.title("🎛️ Panel de Control - Mantenimiento Módulos LED Colombia")

def normalizar_texto(texto):
    """Convierte texto a minúsculas y elimina tildes/acentos para comparaciones exactas."""
    if not isinstance(texto, str):
        texto = str(texto)
    nfkd = unicodedata.normalize('NFD', texto.lower().strip())
    return "".join([c for c in nfkd if not unicodedata.combining(c)])

def procesar_libro_excel(contenido_bytes):
    """Procesa todas las pestañas de un archivo Excel y normaliza columnas de Región y Zona."""
    dict_hojas = pd.read_excel(io.BytesIO(contenido_bytes), sheet_name=None, engine='openpyxl')
    dfs_hoja = []
    hojas_omitir = ['ejemplo', 'hola', 'resumen', 'graficos', 'dashboard']
    
    for nombre_hoja, df_raw in dict_hojas.items():
        if df_raw.empty or normalizar_texto(nombre_hoja) in hojas_omitir:
            continue
            
        # Buscar la fila de encabezados
        header_idx = None
        for idx in range(min(20, len(df_raw))):
            row_vals = [normalizar_texto(v) for v in df_raw.iloc[idx].values if pd.notna(v)]
            if any('cod' in v or 'marca' in v for v in row_vals):
                header_idx = idx
                break
                
        if header_idx is not None:
            headers = [str(v).strip() if pd.notna(v) else f"Col_{i}" for i, v in enumerate(df_raw.iloc[header_idx].values)]
            df = df_raw.iloc[header_idx + 1:].copy().reset_index(drop=True)
            df.columns = headers
        else:
            df = df_raw.copy()
            df.columns = [str(c).strip() if pd.notna(c) else f"Col_{i}" for i, c in enumerate(df.columns)]

        # Desduplicar nombres de columnas
        cols_unicas = []
        vistos = {}
        for col in df.columns:
            c_str = str(col).strip()
            if not c_str or normalizar_texto(c_str) in ['nan', 'unnamed:'] or c_str.startswith('Unnamed:'):
                c_str = "Col_Sin_Nombre"
            if c_str in vistos:
                vistos[c_str] += 1
                cols_unicas.append(f"{c_str}_{vistos[c_str]}")
            else:
                vistos[c_str] = 0
                cols_unicas.append(c_str)
        df.columns = cols_unicas

        # Identificar columna de código
        col_codigo = next((c for c in df.columns if 'cod' in normalizar_texto(c)), None)
        
        if col_codigo:
            df = df[df[col_codigo].notna()]
            df[col_codigo] = df[col_codigo].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
            df = df[~df[col_codigo].apply(normalizar_texto).isin(['nan', '', 'none', 'null', 'codigo', 'col_sin_nombre'])]
            
            if not df.empty:
                df['Pestaña / Sede'] = str(nombre_hoja).strip()
                
                # Buscar columna de Región y Zona
                col_reg_exp = next((c for c in df.columns if 'region' in normalizar_texto(c) or 'regional' in normalizar_texto(c)), None)
                col_zon_exp = next((c for c in df.columns if 'zona' in normalizar_texto(c)), None)
                
                # Asignar valores por defecto si no están definidos
                df['Región'] = df[col_reg_exp].fillna('COLOMBIA').astype(str).str.strip() if col_reg_exp else 'COLOMBIA'
                df['Zona'] = df[col_zon_exp].fillna(str(nombre_hoja).strip()).astype(str).str.strip() if col_zon_exp else str(nombre_hoja).strip()
                
                dfs_hoja.append(df)
                
    return dfs_hoja

@st.cache_data(ttl=60)
def cargar_inventario_nacional():
    file_id = "166rj5uykRRDzjRlcKDa3WCR_f6FeREpc"
    url_xlsx = f"https://docs.google.com/spreadsheets/d/{file_id}/export?format=xlsx"
    
    response = requests.get(url_xlsx, timeout=15)
    if response.status_code != 200:
        url_respaldo = f"https://drive.google.com/uc?export=download&id={file_id}&confirm=t"
        response = requests.get(url_respaldo, timeout=15)
        
    lista_dfs = procesar_libro_excel(response.content)

    if not lista_dfs:
        raise ValueError("No se encontraron registros de módulos en los archivos.")

    df_consolidado = pd.concat(lista_dfs, ignore_index=True)
    
    col_codigo = next((c for c in df_consolidado.columns if 'cod' in normalizar_texto(c)), None)
    col_region = 'Región'
    col_zona = 'Zona'
    col_marca = next((c for c in df_consolidado.columns if 'marca' in normalizar_texto(c)), None)
    col_ubicacion = next((c for c in df_consolidado.columns if 'ubic' in normalizar_texto(c) or 'pantalla' in normalizar_texto(c)), None)

    return df_consolidado, col_codigo, col_region, col_zona, col_marca, col_ubicacion

try:
    df_modulos, col_codigo, col_region, col_zona, col_marca, col_ubicacion = cargar_inventario_nacional()
    st.success(f"✅ Inventario consolidado cargado exitosamente ({len(df_modulos)} módulos registrados)")
except Exception as e:
    st.error("❌ Ocurrió un error al procesar el inventario desde Google Drive:")
    st.exception(e)
    st.stop()

# ----------------------------------------------------
# FILTROS EN CASCADA (REGIÓN -> ZONA -> UBICACIÓN)
# ----------------------------------------------------
st.header("📋 Inventario - FiltrosJerárquicos")

col1, col2, col3, col4 = st.columns(4)

# PASO 1: Selector de Región
with col1:
    regiones_unicas = sorted([
        r for r in df_modulos[col_region].unique() 
        if normalizar_texto(r) not in ['nan', '', 'none', 'null']
    ])
    region_sel = st.multiselect("1. Seleccionar Región", options=regiones_unicas, key="filter_region")

# Filtrar tabla por Región
df_por_region = df_modulos.copy()
if region_sel:
    df_por_region = df_por_region[df_por_region[col_region].isin(region_sel)]

# PASO 2: Selector de Zona (Depende de la Región elegida)
with col2:
    zonas_disponibles = sorted([
        z for z in df_por_region[col_zona].unique() 
        if normalizar_texto(z) not in ['nan', '', 'none', 'null']
    ])
    zona_sel = st.multiselect(
        "2. Seleccionar Zona (Filtrada por Región)", 
        options=zonas_disponibles, 
        key=f"filter_zona_{hash(tuple(sorted(region_sel)))}"
    )

# Filtrar tabla por Zona
df_por_zona = df_por_region.copy()
if zona_sel:
    df_por_zona = df_por_zona[df_por_zona[col_zona].isin(zona_sel)]

# PASO 3: Selector de Marca (Depende de Región y Zona)
with col3:
    if col_marca and col_marca in df_por_zona.columns:
        marcas_disponibles = sorted([
            m for m in df_por_zona[col_marca].astype(str).str.strip().unique() 
            if normalizar_texto(m) not in ['nan', '', 'none', 'null', 'col_sin_nombre']
        ])
        marca_sel = st.multiselect("3. Marca", options=marcas_disponibles, key="filter_marca")
    else:
        marca_sel = []

# PASO 4: Selector de Ubicación / Sede (Depende de Región y Zona)
with col4:
    if col_ubicacion and col_ubicacion in df_por_zona.columns:
        ubic_disponibles = sorted([
            u for u in df_por_zona[col_ubicacion].astype(str).str.strip().unique() 
            if normalizar_texto(u) not in ['nan', '', 'none', 'null', 'col_sin_nombre']
        ])
        ubicacion_sel = st.multiselect("4. Ubicación Actual", options=ubic_disponibles, key="filter_ubicacion")
    else:
        ubicacion_sel = []

# Aplicar filtros adicionales de Marca y Ubicación
df_filtrado = df_por_zona.copy()

if marca_sel and col_marca:
    df_filtrado = df_filtrado[df_filtrado[col_marca].astype(str).str.strip().isin(marca_sel)]

if ubicacion_sel and col_ubicacion:
    df_filtrado = df_filtrado[df_filtrado[col_ubicacion].astype(str).str.strip().isin(ubicacion_sel)]

# Mostrar tabla resultante
st.dataframe(df_filtrado, use_container_width=True, hide_index=True)

# ----------------------------------------------------
# PROGRAMACIÓN DE JORNADAS (CÓDIGOS SEGMENTADOS)
# ----------------------------------------------------
st.header("🛠️ Programar / Registrar Jornada")

codigos_disponibles = sorted(df_filtrado[col_codigo].unique().tolist()) if col_codigo else []

col_sel_1, col_sel_2 = st.columns([2, 1])

with col_sel_1:
    st.info(f"📌 **Módulos listos para seleccionar:** {len(codigos_disponibles)} código(s) en la segmentación actual")

with col_sel_2:
    seleccionar_todos = st.checkbox("✅ Seleccionar TODOS los módulos de este filtro de una vez")

# Key dinámico para actualizar el formulario al cambiar los filtros en cascada
key_form = f"cods_{hash(tuple(sorted(region_sel)))}_{hash(tuple(sorted(zona_sel)))}_{hash(tuple(sorted(marca_sel)))}_{hash(tuple(sorted(ubicacion_sel)))}_{seleccionar_todos}"

with st.form("form_jornada"):
    col_a, col_b = st.columns(2)
    
    with col_a:
        default_codigos = codigos_disponibles if seleccionar_todos else []
        
        codigos_jornada = st.multiselect(
            f"Seleccionar Módulos Específicos ({len(codigos_disponibles)} disponibles)", 
            options=codigos_disponibles,
            default=default_codigos,
            key=key_form
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
