import streamlit as st
import pandas as pd
from datetime import datetime
import requests
import io
import unicodedata

st.set_page_config(page_title="Control Módulos LED Colombia", layout="wide")
st.title("🎛️ Panel de Control - Mantenimiento Módulos LED Colombia")

def normalizar_texto(texto):
    """Convierte texto a minúsculas y elimina tildes/acentos para comparaciones exactas."""
    if not isinstance(texto, str):
        texto = str(texto)
    nfkd = unicodedata.normalize('NFD', texto.lower().strip())
    return "".join([c for c in nfkd if not unicodedata.combining(c)])

@st.cache_data(ttl=60)
def cargar_inventario_nacional():
    file_id = "166rj5uykRRDzjRlcKDa3WCR_f6FeREpc"
    url_xlsx = f"https://docs.google.com/spreadsheets/d/{file_id}/export?format=xlsx"
    
    # 1. Descargar el archivo binario del Excel
    response = requests.get(url_xlsx, timeout=15)
    if response.status_code != 200:
        url_respaldo = f"https://drive.google.com/uc?export=download&id={file_id}&confirm=t"
        response = requests.get(url_respaldo, timeout=15)
        
    excel_data = io.BytesIO(response.content)
    
    # 2. Leer todas las pestañas del archivo
    dict_hojas = pd.read_excel(excel_data, sheet_name=None, engine='openpyxl')
    
    lista_dfs = []
    hojas_omitir = ['ejemplo', 'hola', 'resumen', 'graficos', 'dashboard']
    
    for nombre_hoja, df_raw in dict_hojas.items():
        if df_raw.empty or normalizar_texto(nombre_hoja) in hojas_omitir:
            continue
            
        # 3. Buscar la fila exacta de encabezados ignorando tildes y mayúsculas
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

        # 4. Limpiar y desduplicar nombres de columnas
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

        # 5. Mapear columna de código con normalización de tildes
        col_codigo = next((c for c in df.columns if 'cod' in normalizar_texto(c)), None)
        
        if col_codigo:
            df = df[df[col_codigo].notna()]
            df[col_codigo] = df[col_codigo].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
            df = df[~df[col_codigo].apply(normalizar_texto).isin(['nan', '', 'none', 'null', 'codigo', 'col_sin_nombre'])]
            
            if not df.empty:
                df['Ciudad / Pestaña'] = str(nombre_hoja).strip()
                
                col_zona_existente = next((c for c in df.columns if 'zona' in normalizar_texto(c) or 'region' in normalizar_texto(c)), None)
                if not col_zona_existente:
                    df['Zona'] = str(nombre_hoja).strip()
                else:
                    df[col_zona_existente] = df[col_zona_existente].fillna(str(nombre_hoja).strip())
                    
                lista_dfs.append(df)

    if not lista_dfs:
        raise ValueError("No se encontraron registros de códigos válidos en el archivo.")

    # 6. Consolidar todas las pestañas de Colombia en una sola tabla
    df_consolidado = pd.concat(lista_dfs, ignore_index=True)
    
    col_codigo = next((c for c in df_consolidado.columns if 'cod' in normalizar_texto(c)), None)
    col_zona = next((c for c in df_consolidado.columns if 'zona' in normalizar_texto(c) or 'region' in normalizar_texto(c)), None)
    col_marca = next((c for c in df_consolidado.columns if 'marca' in normalizar_texto(c)), None)
    col_ubicacion = next((c for c in df_consolidado.columns if 'ubic' in normalizar_texto(c) or 'pantalla' in normalizar_texto(c)), None)

    return df_consolidado, col_codigo, col_zona, col_marca, col_ubicacion

try:
    df_modulos, col_codigo, col_zona, col_marca, col_ubicacion = cargar_inventario_nacional()
    st.success(f"✅ Inventario consolidado cargado exitosamente ({len(df_modulos)} módulos totales encontrados)")
except Exception as e:
    st.error("❌ Ocurrió un error al procesar el archivo Excel de Google Drive:")
    st.exception(e)
    st.stop()

# ----------------------------------------------------
# FILTROS Y SEGMENTACIÓN POR ZONA Y CIUDAD
# ----------------------------------------------------
st.header("📋 Inventario Nacional - Filtros de Segmentación")

col1, col2, col3, col4 = st.columns(4)

with col1:
    if col_zona and col_zona in df_modulos.columns:
        zonas_unicas = sorted([
            z for z in df_modulos[col_zona].astype(str).str.strip().unique() 
            if normalizar_texto(z) not in ['nan', '', 'none', 'null', 'col_sin_nombre']
        ])
        zona_sel = st.multiselect("Filtrar por Zona / Región", options=zonas_unicas)
    else:
        zona_sel = []

with col2:
    ciudades_unicas = sorted([
        c for c in df_modulos['Ciudad / Pestaña'].astype(str).str.strip().unique() 
        if normalizar_texto(c) not in ['nan', '', 'none', 'null']
    ])
    ciudad_sel = st.multiselect("Filtrar por Pestaña / Ciudad", options=ciudades_unicas)

with col3:
    if col_marca and col_marca in df_modulos.columns:
        marcas_unicas = sorted([
            m for m in df_modulos[col_marca].astype(str).str.strip().unique() 
            if normalizar_texto(m) not in ['nan', '', 'none', 'null', 'col_sin_nombre']
        ])
        marca_sel = st.multiselect("Filtrar por Marca", options=marcas_unicas)
    else:
        marca_sel = []

with col4:
    if col_ubicacion and col_ubicacion in df_modulos.columns:
        ubic_unicas = sorted([
            u for u in df_modulos[col_ubicacion].astype(str).str.strip().unique() 
            if normalizar_texto(u) not in ['nan', '', 'none', 'null', 'col_sin_nombre']
        ])
        ubicacion_sel = st.multiselect("Filtrar por Ubicación", options=ubic_unicas)
    else:
        ubicacion_sel = []

# Aplicar filtros combinados
df_filtrado = df_modulos.copy()

if zona_sel and col_zona:
    df_filtrado = df_filtrado[df_filtrado[col_zona].astype(str).str.strip().isin(zona_sel)]

if ciudad_sel:
    df_filtrado = df_filtrado[df_filtrado['Ciudad / Pestaña'].astype(str).str.strip().isin(ciudad_sel)]

if marca_sel and col_marca:
    df_filtrado = df_filtrado[df_filtrado[col_marca].astype(str).str.strip().isin(marca_sel)]

if ubicacion_sel and col_ubicacion:
    df_filtrado = df_filtrado[df_filtrado[col_ubicacion].astype(str).str.strip().isin(ubicacion_sel)]

st.dataframe(df_filtrado, use_container_width=True, hide_index=True)

# ----------------------------------------------------
# PROGRAMACIÓN DE JORNADAS CON CÓDIGOS SEGMENTADOS
# ----------------------------------------------------
st.header("🛠️ Programar / Registrar Jornada")

st.info(f"📌 **Módulos disponibles en el filtro actual:** {len(df_filtrado)} código(s)")

with st.form("form_jornada"):
    col_a, col_b = st.columns(2)
    
    with col_a:
        codigos_disponibles = sorted(df_filtrado[col_codigo].unique().tolist()) if col_codigo else []
        codigos_jornada = st.multiselect(
            f"Seleccionar Módulos ({len(codigos_disponibles)} disponibles según filtro)", 
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
