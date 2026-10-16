import streamlit as st
import pandas as pd
from datetime import datetime
import requests
import io

st.set_page_config(page_title="Control Módulos LED Colombia", layout="wide")
st.title("🎛️ Panel de Control - Mantenimiento Módulos LED Colombia")

@st.cache_data(ttl=60)
def cargar_inventario_nacional():
    file_id = "166rj5uykRRDzjRlcKDa3WCR_f6FeREpc"
    url_xlsx = f"https://docs.google.com/spreadsheets/d/{file_id}/export?format=xlsx"
    
    # 1. Descarga binaria segura mediante requests
    response = requests.get(url_xlsx, timeout=15)
    if response.status_code != 200:
        # Intento de respaldo si la exportación directa falla
        url_respaldo = f"https://drive.google.com/uc?export=download&id={file_id}&confirm=t"
        response = requests.get(url_respaldo, timeout=15)
        
    excel_data = io.BytesIO(response.content)
    
    # 2. Leer todas las pestañas del libro Excel
    dict_hojas = pd.read_excel(excel_data, sheet_name=None, engine='openpyxl')
    
    lista_dfs = []
    hojas_omitir = ['ejemplo', 'hola', 'resumen', 'graficos', 'dashboard']
    
    for nombre_hoja, df_raw in dict_hojas.items():
        if df_raw.empty or str(nombre_hoja).lower().strip() in hojas_omitir:
            continue
            
        # 3. Buscar la fila exacta donde inician los encabezados ('Código', 'Cod', 'Marca', etc.)
        header_idx = None
        for idx in range(len(df_raw)):
            row_vals = [str(v).lower().strip() for v in df_raw.iloc[idx].values if pd.notna(v)]
            if any('cod' in v for v in row_vals):
                header_idx = idx
                break
                
        if header_idx is not None:
            headers = [str(v).strip() if pd.notna(v) else f"Col_{i}" for i, v in enumerate(df_raw.iloc[header_idx].values)]
            df = df_raw.iloc[header_idx + 1:].copy().reset_index(drop=True)
            df.columns = headers
        else:
            df = df_raw.copy()
            df.columns = [str(c).strip() if pd.notna(c) else f"Col_{i}" for i, c in enumerate(df.columns)]

        # 4. Limpieza y desduplicación de nombres de columna
        cols_unicas = []
        vistos = {}
        for col in df.columns:
            c_str = str(col).strip()
            if not c_str or c_str.lower() in ['nan', 'unnamed:'] or c_str.startswith('Unnamed:'):
                c_str = "Col_Sin_Nombre"
            if c_str in vistos:
                vistos[c_str] += 1
                cols_unicas.append(f"{c_str}_{vistos[c_str]}")
            else:
                vistos[c_str] = 0
                cols_unicas.append(c_str)
        df.columns = cols_unicas

        # 5. Mapeo de la columna 'Código'
        col_codigo = next((c for c in df.columns if 'cod' in c.lower()), None)
        
        if col_codigo:
            df = df[df[col_codigo].notna()]
            df[col_codigo] = df[col_codigo].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
            df = df[~df[col_codigo].str.lower().isin(['nan', '', 'none', 'null', 'código', 'codigo', 'col_sin_nombre'])]
            
            if not df.empty:
                # Asignar Ciudad o Pestaña de origen
                df['Ciudad / Pestaña'] = str(nombre_hoja).strip()
                
                # Si no existe columna de Zona, asignar por defecto el nombre de la pestaña
                col_zona_existente = next((c for c in df.columns if 'zona' in c.lower()), None)
                if not col_zona_existente:
                    df['Zona'] = str(nombre_hoja).strip()
                else:
                    df[col_zona_existente] = df[col_zona_existente].fillna(str(nombre_hoja).strip())
                    
                lista_dfs.append(df)

    if not lista_dfs:
        raise ValueError("No se encontraron registros de códigos válidos en el libro de Excel.")

    # 6. Consolida todas las pestañas en un solo DataFrame
    df_consolidado = pd.concat(lista_dfs, ignore_index=True)
    
    col_codigo = next((c for c in df_consolidado.columns if 'cod' in c.lower()), None)
    col_zona = next((c for c in df_consolidado.columns if 'zona' in c.lower()), None)
    col_marca = next((c for c in df_consolidado.columns if 'marca' in c.lower()), None)
    col_ubicacion = next((c for c in df_consolidado.columns if 'ubic' in c.lower() or 'pantalla' in c.lower()), None)

    return df_consolidado, col_codigo, col_zona, col_marca, col_ubicacion

try:
    df_modulos, col_codigo, col_zona, col_marca, col_ubicacion = cargar_inventario_nacional()
    st.success(f"✅ Inventario consolidado cargado exitosamente ({len(df_modulos)} módulos encontrados en total)")
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
            if z.lower() not in ['nan', '', 'none', 'null', 'col_sin_nombre']
        ])
        zona_sel = st.multiselect("Filtrar por Zona", options=zonas_unicas)
    else:
        zona_sel = []

with col2:
    ciudades_unicas = sorted([
        c for c in df_modulos['Ciudad / Pestaña'].astype(str).str.strip().unique() 
        if c.lower() not in ['nan', '', 'none', 'null']
    ])
    ciudad_sel = st.multiselect("Filtrar por Ciudad / Pestaña", options=ciudades_unicas)

with col3:
    if col_marca and col_marca in df_modulos.columns:
        marcas_unicas = sorted([
            m for m in df_modulos[col_marca].astype(str).str.strip().unique() 
            if m.lower() not in ['nan', '', 'none', 'null', 'col_sin_nombre']
        ])
        marca_sel = st.multiselect("Filtrar por Marca", options=marcas_unicas)
    else:
        marca_sel = []

with col4:
    if col_ubicacion and col_ubicacion in df_modulos.columns:
        ubic_unicas = sorted([
            u for u in df_modulos[col_ubicacion].astype(str).str.strip().unique() 
            if u.lower() not in ['nan', '', 'none', 'null', 'col_sin_nombre']
        ])
        ubicacion_sel = st.multiselect("Filtrar por Ubicación", options=ubic_unicas)
    else:
        ubicacion_sel = []

# Filtrado reactivo
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

st.info(f"📌 **Módulos filtrados disponibles:** {len(df_filtrado)} código(s)")

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
