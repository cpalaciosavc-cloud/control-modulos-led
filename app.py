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
    
    df = pd.read_csv(url_csv)
    
    # 1. Limpiar espacios en blanco en los nombres de las columnas
    df.columns = df.columns.astype(str).str.strip()
    
    # 2. Detectar dinámicamente la columna 'Zona'
    col_zona = None
    for col in df.columns:
        if col.lower() in ['zona', 'zona regional', 'region', 'región']:
            col_zona = col
            break
            
    # 3. Eliminar espacios invisibles en todas las celdas de texto
    for col in df.select_dtypes(include='object').columns:
        df[col] = df[col].astype(str).str.strip()
        
    # 4. Limpiar columna de Código
    col_codigo = next((c for c in df.columns if 'cód' in c.lower() or 'cod' in c.lower()), None)
    if col_codigo:
        df = df[df[col_codigo].notna() & (df[col_codigo] != '') & (df[col_codigo] != 'nan')]
        df[col_codigo] = df[col_codigo].str.replace('.0', '', regex=False)
        
    return df, col_zona

try:
    df_modulos, col_zona = cargar_inventario()
    st.success("✅ Inventario cargado exitosamente")
except Exception as e:
    st.error("❌ Ocurrió un error al cargar la hoja de cálculo:")
    st.exception(e)
    st.stop()

# ----------------------------------------------------
# VISUALIZACIÓN Y FILTROS
# ----------------------------------------------------
st.header("📋 Inventario Actual")

col1, col2, col3 = st.columns(3)

# Identificar columnas clave automáticamente
col_codigo = next((c for c in df_modulos.columns if 'cód' in c.lower() or 'cod' in c.lower()), df_modulos.columns[0])
col_marca = next((c for c in df_modulos.columns if 'marca' in c.lower()), None)
col_ubicacion = next((c for c in df_modulos.columns if 'ubicaci' in c.lower()), None)

with col1:
    if col_zona and col_zona in df_modulos.columns:
        # Extraer zonas únicas ignorando valores nulos o vacíos
        zonas_unicas = sorted([z for z in df_modulos[col_zona].unique() if z and z.lower() != 'nan'])
        zona_sel = st.multiselect("Filtrar por Zona", options=zonas_unicas)
    else:
        st.info("Columna 'Zona' no detectada")
        zona_sel = []

with col2:
    if col_marca and col_marca in df_modulos.columns:
        marcas_unicas = sorted([m for m in df_modulos[col_marca].unique() if m and m.lower() != 'nan'])
        marca_sel = st.multiselect("Filtrar por Marca", options=marcas_unicas)
    else:
        marca_sel = []

with col3:
    if col_ubicacion and col_ubicacion in df_modulos.columns:
        ubic_unicas = sorted([u for u in df_modulos[col_ubicacion].unique() if u and u.lower() != 'nan'])
        ubicacion_sel = st.multiselect("Filtrar por Ubicación", options=ubic_unicas)
    else:
        ubicacion_sel = []

# Aplicación de los filtros combinados
df_filtrado = df_modulos.copy()

if zona_sel and col_zona:
    df_filtrado = df_filtrado[df_filtrado[col_zona].isin(zona_sel)]

if marca_sel and col_marca:
    df_filtrado = df_filtrado[df_filtrado[col_marca].isin(marca_sel)]

if ubicacion_sel and col_ubicacion:
    df_filtrado = df_filtrado[df_filtrado[col_ubicacion].isin(ubicacion_sel)]

st.dataframe(df_filtrado, use_container_width=True, hide_index=True)

# ----------------------------------------------------
# FORMULARIO DE REGISTRO DE JORNADA
# ----------------------------------------------------
st.header("🛠️ Programar / Registrar Jornada")

with st.form("form_jornada"):
    col_a, col_b = st.columns(2)
    
    with col_a:
        codigos_disponibles = df_filtrado[col_codigo].dropna().unique().tolist()
        codigos_jornada = st.multiselect("Seleccionar Módulos (Códigos)", options=codigos_disponibles)
        
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
