import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Control Módulos LED Colombia", layout="wide")
st.title("🎛️ Panel de Control - Mantenimiento Módulos LED")

def desduplicar_columnas(columnas):
    """Asegura que todos los nombres de columnas sean únicos para evitar errores de PyArrow/Streamlit."""
    vistos = {}
    resultado = []
    for col in columnas:
        nombre = str(col).strip()
        if not nombre or nombre.lower() in ['nan', 'unnamed:']:
            nombre = "Columna_Sin_Nombre"
            
        if nombre in vistos:
            vistos[nombre] += 1
            resultado.append(f"{nombre}_{vistos[nombre]}")
        else:
            vistos[nombre] = 0
            resultado.append(nombre)
    return resultado

@st.cache_data(ttl=60)
def cargar_inventario():
    sheet_id = "166rj5uykRRDzjRlcKDa3WCR_f6FeREpc"
    gid = "995802095"
    url_csv = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
    
    # 1. Cargar el CSV
    df = pd.read_csv(url_csv)
    
    # 2. Detectar si la primera fila es un título y ajustar la fila de encabezados
    columnas_txt = [str(c).lower() for c in df.columns]
    if not any('cod' in c or 'zona' in c or 'marca' in c for c in columnas_txt):
        for i in range(min(5, len(df))):
            row_vals = [str(v).lower() for v in df.iloc[i].tolist()]
            if any('cod' in v or 'zona' in v or 'marca' in v for v in row_vals):
                df.columns = df.iloc[i].astype(str)
                df = df.iloc[i+1:].reset_index(drop=True)
                break

    # 3. Desduplicar y limpiar los nombres de columnas
    df.columns = desduplicar_columnas(df.columns)
    
    # 4. Detección flexible de columnas clave
    col_codigo = next((c for c in df.columns if 'cod' in c.lower() or 'cód' in c.lower()), None)
    col_zona = next((c for c in df.columns if 'zona' in c.lower() or 'region' in c.lower() or 'región' in c.lower()), None)
    col_marca = next((c for c in df.columns if 'marca' in c.lower()), None)
    col_ubicacion = next((c for c in df.columns if 'ubic' in c.lower() or 'pantalla' in c.lower() or 'sede' in c.lower()), None)
    
    # 5. Limpieza de filas nulas o inválidas en la columna del código
    if col_codigo:
        df = df[df[col_codigo].notna()]
        df = df[~df[col_codigo].astype(str).str.lower().isin(['nan', '', 'none', 'null', 'columna_sin_nombre'])]
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
# VISOR DE DEPURACIÓN DE COLUMNAS
# ----------------------------------------------------
with st.expander("🔍 Ver columnas detectadas en el archivo (Depuración)"):
    st.write("**Columnas encontradas:**", list(df_modulos.columns))
    st.write(f"- **Columna Código:** `{col_codigo}`")
    st.write(f"- **Columna Zona:** `{col_zona}`")
    st.write(f"- **Columna Marca:** `{col_marca}`")
    st.write(f"- **Columna Ubicación:** `{col_ubicacion}`")

# ----------------------------------------------------
# VISUALIZACIÓN Y FILTROS
# ----------------------------------------------------
st.header("📋 Inventario Actual")

col1, col2, col3 = st.columns(3)

with col1:
    if col_zona:
        zonas_unicas = sorted([z for z in df_modulos[col_zona].astype(str).str.strip().unique() if z.lower() not in ['nan', '', 'none', 'null']])
        zona_sel = st.multiselect("Filtrar por Zona", options=zonas_unicas)
    else:
        st.warning("Columna 'Zona' no detectada")
        zona_sel = []

with col2:
    if col_marca:
        marcas_unicas = sorted([m for m in df_modulos[col_marca].astype(str).str.strip().unique() if m.lower() not in ['nan', '', 'none', 'null']])
        marca_sel = st.multiselect("Filtrar por Marca", options=marcas_unicas)
    else:
        marca_sel = []

with col3:
    if col_ubicacion:
        ubic_unicas = sorted([u for u in df_modulos[col_ubicacion].astype(str).str.strip().unique() if u.lower() not in ['nan', '', 'none', 'null']])
        ubicacion_sel = st.multiselect("Filtrar por Ubicación", options=ubic_unicas)
    else:
        ubicacion_sel = []

# Aplicar filtros combinados
df_filtrado = df_modulos.copy()

if zona_sel and col_zona:
    df_filtrado = df_filtrado[df_filtrado[col_zona].astype(str).str.strip().isin(zona_sel)]

if marca_sel and col_marca:
    df_filtrado = df_filtrado[df_filtrado[col_marca].astype(str).str.strip().isin(marca_sel)]

if ubicacion_sel and col_ubicacion:
    df_filtrado = df_filtrado[df_filtrado[col_ubicacion].astype(str).str.strip().isin(ubicacion_sel)]

st.dataframe(df_filtrado, use_container_width=True, hide_index=True)

# ----------------------------------------------------
# FORMULARIO DE REGISTRO DE JORNADA
# ----------------------------------------------------
st.header("🛠️ Programar / Registrar Jornada")

with st.form("form_jornada"):
    col_a, col_b = st.columns(2)
    
    with col_a:
        codigos_disponibles = sorted(df_filtrado[col_codigo].unique().tolist()) if col_codigo else []
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
