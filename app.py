import streamlit as st
import pandas as pd
from datetime import datetime

# 1. Configuración de la página
st.set_page_config(page_title="Control Módulos LED Colombia", layout="wide")
st.title("🎛️ Panel de Control - Mantenimiento Módulos LED")

# 2. Carga directa de tu Google Sheet mediante enlace CSV público
@st.cache_data(ttl=60)  # Se actualiza cada 60 segundos
def cargar_inventario():
    # ID y GID exactos de tu hoja de Google Drive
    sheet_id = "166rj5uykRRDzjRlcKDa3WCR_f6FeREpc"
    gid = "995802095"
    url_csv = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
    
    # Lectura directa con pandas (no requiere st.secrets)
    df = pd.read_csv(url_csv)
    
    # Limpieza de datos
    if 'Código' in df.columns:
        df = df.dropna(subset=['Código'])
        df['Código'] = df['Código'].astype(str).str.replace('.0', '', regex=False)
    
    return df

# Control de carga con muestra de error detallada
try:
    df_modulos = cargar_inventario()
    st.success("✅ Inventario cargado exitosamente desde Google Sheets")
except Exception as e:
    st.error("❌ Ocurrió un error al leer la hoja de cálculo:")
    st.exception(e)  # Muestra el error técnico real de Python en pantalla
    st.stop()

# 3. Vista de Inventario y Filtros
st.header("📋 Inventario Actual")

col1, col2, col3 = st.columns(3)

with col1:
    zonas = df_modulos['Zona'].dropna().unique().tolist() if 'Zona' in df_modulos.columns else []
    zona_sel = st.multiselect("Filtrar por Zona", zonas)

with col2:
    marcas = df_modulos['Marca'].dropna().unique().tolist() if 'Marca' in df_modulos.columns else []
    marca_sel = st.multiselect("Filtrar por Marca", marcas)

with col3:
    ubicaciones = df_modulos['Ubicacion actual'].dropna().unique().tolist() if 'Ubicacion actual' in df_modulos.columns else []
    ubicacion_sel = st.multiselect("Filtrar por Ubicación", ubicaciones)

# Aplicar filtros
df_filtrado = df_modulos.copy()
if zona_sel:
    df_filtrado = df_filtrado[df_filtrado['Zona'].isin(zona_sel)]
if marca_sel:
    df_filtrado = df_filtrado[df_filtrado['Marca'].isin(marca_sel)]
if ubicacion_sel:
    df_filtrado = df_filtrado[df_filtrado['Ubicacion actual'].isin(ubicacion_sel)]

# Selección de columnas visibles
cols_visibles = [c for c in ['Código', 'Región', 'Zona', 'Marca', 'Modelo', 'Pitch', 'Ubicacion actual'] if c in df_filtrado.columns]
st.dataframe(df_filtrado[cols_visibles], use_container_width=True, hide_index=True)

# 4. Formulario de Programación de Jornadas por Bimestre
st.header("🛠️ Programar / Registrar Jornada")

with st.form("form_jornada"):
    col_a, col_b = st.columns(2)
    
    with col_a:
        codigos_disponibles = df_filtrado['Código'].tolist() if 'Código' in df_filtrado.columns else []
        codigos_jornada = st.multiselect("Seleccionar Módulos (Códigos)", codigos_disponibles)
        
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
            # Cálculo automático del bimestre (B1 a B6)
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
