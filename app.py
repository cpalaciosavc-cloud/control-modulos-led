import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# ==========================================
# 1. CONFIGURACIÓN DE LA PÁGINA
# ==========================================
st.set_page_config(page_title="Control Módulos LED Colombia", layout="wide")
st.title("🎛️ Panel de Control - Mantenimiento Módulos LED")

# ==========================================
# 2. CONEXIÓN A TU ARCHIVO DE DRIVE
# ==========================================
@st.cache_data(ttl=600) # Se actualiza cada 10 minutos
def cargar_inventario_drive():
    # Conectamos a Google Sheets usando el enlace de tu archivo
    conn = st.connection("gsheets", type=GSheetsConnection)
    url_archivo = "https://docs.google.com/spreadsheets/d/166rj5uykRRDzjRlcKDa3WCR_f6FeREpc/edit?gid=995802095#gid=995802095"
    
    # Leemos la hoja de cálculo
    df = conn.read(spreadsheet=url_archivo)
    # Limpiamos filas vacías
    df = df.dropna(subset=['Código'])
    # Convertimos el código a string para evitar decimales si lo lee como número
    df['Código'] = df['Código'].astype(str).str.replace('.0', '', regex=False)
    return df

try:
    df_modulos = cargar_inventario_drive()
    st.success("✅ Inventario cargado exitosamente desde Drive")
except Exception as e:
    st.error("Error al cargar el archivo. Verifica los permisos de st.secrets.")
    st.stop()

# ==========================================
# 3. INTERFAZ: INVENTARIO ACTUAL
# ==========================================
st.header("📋 Inventario Actual")

# Filtros adaptados a tus columnas
col1, col2, col3 = st.columns(3)
with col1:
    zonas = df_modulos['Zona'].dropna().unique().tolist()
    zona_seleccionada = st.multiselect("Filtrar por Zona", zonas, default=[])
with col2:
    marcas = df_modulos['Marca'].dropna().unique().tolist()
    marca_seleccionada = st.multiselect("Filtrar por Marca (Ej. ABSEN, GENERICA)", marcas, default=[])
with col3:
    ubicaciones = df_modulos['Ubicacion actual'].dropna().unique().tolist()
    ubicacion_seleccionada = st.multiselect("Filtrar por Ubicación", ubicaciones, default=[])

# Aplicar filtros
df_filtrado = df_modulos.copy()
if zona_seleccionada:
    df_filtrado = df_filtrado[df_filtrado['Zona'].isin(zona_seleccionada)]
if marca_seleccionada:
    df_filtrado = df_filtrado[df_filtrado['Marca'].isin(marca_seleccionada)]
if ubicacion_seleccionada:
    df_filtrado = df_filtrado[df_filtrado['Ubicacion actual'].isin(ubicacion_seleccionada)]

# Mostrar tabla (mostrando solo columnas relevantes para que sea más limpio)
st.dataframe(
    df_filtrado[['Código', 'Zona', 'Marca', 'Modelo', 'Pitch', 'Ubicacion actual']], 
    use_container_width=True,
    hide_index=True
)

# ==========================================
# 4. INTERFAZ: PROGRAMAR JORNADA
# ==========================================
st.header("🛠️ Registrar / Programar Jornada")

with st.form("form_jornada"):
    col_a, col_b = st.columns(2)
    
    with col_a:
        # Extraemos los códigos directamente de la columna "Código" de tu archivo
        codigos_disponibles = df_filtrado['Código'].tolist()
        codigos_jornada = st.multiselect("Seleccionar Módulos (Códigos)", codigos_disponibles)
        
        tipo_jornada = st.selectbox("Tipo de Jornada", [
            "Mantenimiento Preventivo", 
            "Conteo de LED Fallidos", 
            "Mantenimiento Correctivo", 
            "Limpieza / Ajuste"
        ])
    
    with col_b:
        fecha_jornada = st.date_input("Fecha Programada", datetime.today())
        tecnico = st.text_input("Técnico Asignado")
        notas = st.text_area("Observaciones")
        
    submit = st.form_submit_button("Registrar Jornada")
    
    if submit:
        if not codigos_jornada:
            st.warning("Debes seleccionar al menos un código de módulo.")
        else:
            # Cálculo automático del bimestre (1 a 6)
            bimestre_num = (fecha_jornada.month - 1) // 2 + 1
            bimestre_id = f"{fecha_jornada.year}-B{bimestre_num}"
            
            st.success(f"✅ Jornada '{tipo_jornada}' programada para {len(codigos_jornada)} módulos en el bimestre {bimestre_id}.")
            
            # Aquí te mostraría un resumen de los datos a guardar en una base de datos o en una pestaña nueva de Google Sheets
            st.info("Datos listos para registrar en historial:")
            datos_registro = pd.DataFrame({
                "Bimestre": [bimestre_id] * len(codigos_jornada),
                "Fecha": [fecha_jornada] * len(codigos_jornada),
                "Código Módulo": codigos_jornada,
                "Tipo Jornada": [tipo_jornada] * len(codigos_jornada),
                "Técnico": [tecnico] * len(codigos_jornada)
            })
            st.dataframe(datos_registro, hide_index=True)
