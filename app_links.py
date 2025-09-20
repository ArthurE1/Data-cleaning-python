# app_links.py
# ------------------------------------------------------------
# Links & Comparación de tiendas (Streamlit)
# ------------------------------------------------------------
# Qué hace esta app:
# 1) (Original) Depurar links por tienda a partir de un Excel:
#    - Permite elegir la hoja, la columna TIENDA y la columna LINK/URL.
#    - Limpia y deduplica pares (tienda, link).
#    - Muestra 3 vistas (filas, columnas, texto con saltos).
#    - Descarga un Excel con todas las vistas.
#
# 2) === NUEVO === Comparar tiendas entre dos archivos (CSV o Excel):
#    - Cargas Archivo A y Archivo B (acepta .csv o .xlsx).
#    - Eliges la columna que corresponde a TIENDA en cada archivo.
#    - Muestra Coincidencias, Solo en A (faltan en B), Solo en B (faltan en A).
#    - (Opcional) Agrega hojas con links por tienda y una comparativa lado a lado.
#    - Descarga un Excel con todas las tablas.
#    === /NUEVO ===
#
# Requisitos:
#   pip install streamlit pandas openpyxl
# Ejecución:
#   streamlit run app_links.py
# ------------------------------------------------------------

import io
from pathlib import Path
import pandas as pd
import streamlit as st

# ------------------------------------------------------------
# Configuración básica de la página
# ------------------------------------------------------------
st.set_page_config(page_title="Links & Comparación de tiendas", page_icon="🧰", layout="wide")

# ------------------------------------------------------------
# Utilidades comunes (funciones pequeñas y reutilizables)
# ------------------------------------------------------------
def leer_tabla(uploaded_file):
    """
    Lee un CSV o un XLSX subido y devuelve (df, nombre_hoja).
    - Si es CSV: no hay hoja -> retorna (df, None).
    - Si es XLSX: pregunta por la hoja y la usa.
    """
    name = uploaded_file.name.lower()
    if name.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
        return df, None
    elif name.endswith(".xlsx"):
        xls = pd.ExcelFile(uploaded_file)
        hoja = st.selectbox(f"Hoja en {uploaded_file.name}:", xls.sheet_names, index=0, key=f"hoja_{uploaded_file.name}")
        df = pd.read_excel(uploaded_file, sheet_name=hoja)
        return df, hoja
    else:
        st.error("Formato no soportado. Usa .csv o .xlsx")
        return pd.DataFrame(), None

def limpiar_df(df: pd.DataFrame) -> pd.DataFrame:
    """
    Limpia columnas 'Unnamed', estandariza encabezados y normaliza la columna 'tienda' si existe.
    - Elimina columnas que empiecen por 'Unnamed'.
    - recorta espacios en nombres de columnas.
    - en 'tienda': quita espacios extremos y colapsa espacios múltiples.
    """
    if df.empty:
        return df.copy()
    # Eliminar columnas automáticas 'Unnamed'
    df = df.loc[:, ~df.columns.str.contains(r"^Unnamed", case=False, regex=True)].copy()
    # Nombres de columnas sin espacios extremos
    df.columns = [str(c).strip() for c in df.columns]
    # Normaliza 'tienda'
    if "tienda" in df.columns:
        df["tienda"] = (
            df["tienda"]
            .astype(str)
            .str.strip()
            .str.replace(r"\s+", " ", regex=True)
        )
    return df

def detectar_cols_link(df: pd.DataFrame):
    """Devuelve las columnas cuyo nombre empieza con 'link' (insensible a mayúsculas)."""
    return [c for c in df.columns if str(c).lower().startswith("link")]

def elegir_columna_tienda(df: pd.DataFrame, key="tienda"):
    """
    Muestra un select para que el usuario elija qué columna representa la TIENDA.
    - Si existe 'tienda', la pone como default.
    """
    cols = list(df.columns)
    default = cols.index("tienda") if "tienda" in cols else 0
    return st.selectbox("Columna TIENDA:", cols, index=int(default), key=key)

def links_por_fila(row, link_cols):
    """A partir de varias columnas de links, junta los valores no vacíos, sin duplicados y respetando el orden."""
    vals = []
    for c in link_cols:
        v = row.get(c, None)
        if pd.notna(v) and str(v).strip():
            vals.append(str(v).strip())
    # Únicos manteniendo orden
    seen, ordered = set(), []
    for v in vals:
        if v not in seen:
            ordered.append(v)
            seen.add(v)
    return ordered

def agregar_links_por_tienda(df: pd.DataFrame) -> pd.DataFrame:
    """
    Devuelve una tabla [tienda, links], donde 'links' es la lista combinada
    (única y ordenada) de link_1..link_n (o de la columna 'link' si existe).
    """
    link_cols = detectar_cols_link(df)
    if not link_cols and "link" in df.columns:
        link_cols = ["link"]
    if not link_cols:
        base = df[["tienda"]].drop_duplicates().copy()
        base["links"] = [[] for _ in range(len(base))]
        return base
    tmp = df.copy()
    tmp["links"] = tmp.apply(lambda r: links_por_fila(r, link_cols), axis=1)
    agg = (
        tmp.groupby("tienda", dropna=False)["links"]
        .apply(lambda lists: list(dict.fromkeys([v for sub in lists for v in sub])))
        .reset_index()
    )
    return agg

def descargar_excel(dfs: dict, nombre: str = "resultado.xlsx") -> bytes:
    """
    Recibe un dict {'NombreHoja': DataFrame, ...} y devuelve los bytes de un Excel con todas las hojas.
    Útil para descargar múltiples vistas/tablas en un solo archivo.
    """
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        for hoja, data in dfs.items():
            # Excel limita el nombre de hoja a 31 caracteres
            data.to_excel(writer, sheet_name=str(hoja)[:31], index=False)
    buffer.seek(0)
    return buffer.read()

# ------------------------------------------------------------
# Sidebar / Menú de navegación
# ------------------------------------------------------------
st.sidebar.title("Menú")
modo = st.sidebar.radio(
    "Elige una sección:",
    [
        "🧹 Depurar links por tienda (Excel)",
        # === NUEVO ===
        "🧩 Comparar tiendas (CSV o Excel)",
        # === /NUEVO ===
    ],
)

st.sidebar.caption("Requisitos: columna **tienda** y una columna con **http** para links (o columnas link_*).")

# ------------------------------------------------------------
# MODO 1: Depurar links por tienda (tu flujo original, Excel)
# ------------------------------------------------------------
if modo.startswith("🧹"):
    st.title("Depurar links por tienda (Excel)")

    # Sube un Excel (misma UX que tu app original)
    up = st.file_uploader("Arrastra tu Excel (.xlsx)", type=["xlsx"], key="depurar_up")

    if not up:
        st.info("Sube un archivo para empezar.")
    else:
        # (1) Seleccionar hoja
        xls = pd.ExcelFile(up)
        hoja = st.selectbox("Hoja:", xls.sheet_names, index=0, key="depurar_hoja")
        df = pd.read_excel(up, sheet_name=hoja)

        # (2) Elegir columnas TIENDA y LINK/URL
        cols = list(df.columns)

        tienda_idx = cols.index("tienda") if "tienda" in cols else 0
        col_tienda = st.selectbox("Columna TIENDA:", cols, index=int(tienda_idx), key="depurar_tienda")

        # Heurística para elegir por defecto la columna de links
        prefer = ["id_visita (URL extraída)", "link", "id_visita"]
        if any(c in cols for c in prefer):
            col_link_default = next(c for c in prefer if c in cols)
        else:
            col_link_default = next(
                (c for c in cols if df[c].astype(str).str.contains("http", case=False, na=False).any()),
                cols[0]
            )
        link_idx = cols.index(col_link_default)
        col_link = st.selectbox("Columna LINK/URL:", cols, index=int(link_idx), key="depurar_link")

        # (3) Limpiar y deduplicar (tienda, link)
        base = (
            df[[col_tienda, col_link]]
            .dropna()
            .astype(str)
            .assign(**{
                col_tienda: lambda x: x[col_tienda].str.strip(),
                col_link:   lambda x: x[col_link].str.strip(),
            })
        )
        base = base[base[col_link] != ""]
        base.columns = ["tienda", "link"]

        pares_unicos = (
            base.drop_duplicates(subset=["tienda", "link"])
                .sort_values(["tienda", "link"])
                .reset_index(drop=True)
        )

        # (4) Tres vistas de salida
        links_por_filas = pares_unicos.copy()

        grupos = pares_unicos.groupby("tienda")["link"].apply(list).reset_index()
        max_links = int(grupos["link"].str.len().max()) if not grupos.empty else 0
        wide = pd.DataFrame({"tienda": grupos["tienda"]})
        for i in range(max_links):
            wide[f"link_{i+1}"] = grupos["link"].apply(lambda lst, i=i: lst[i] if i < len(lst) else "")

        links_por_tienda = (
            pares_unicos.groupby("tienda")["link"]
            .agg(["nunique", lambda s: "\n".join(s.unique())])
            .reset_index()
            .rename(columns={"nunique": "links_unicos", "<lambda_0>": "links_unicos_list"})
            .sort_values("tienda")
        )

        # (5) Métricas y selector de vista
        col1, col2, col3 = st.columns(3)
        col1.metric("Pares únicos", len(pares_unicos))
        col2.metric("Tiendas", links_por_tienda.shape[0])
        prom = round(links_por_tienda["links_unicos"].mean(), 2) if not links_por_tienda.empty else 0
        col3.metric("Promedio links únicos/tienda", prom)

        vista = st.radio(
            "Vista en pantalla",
            ["Una fila por link (recomendado)", "Links en columnas (MÁS RECOMENDADO)", "Texto con saltos de línea"],
            index=0,
            key="depurar_vista"
        )

        if vista == "Una fila por link (recomendado)":
            st.dataframe(links_por_filas, use_container_width=True, height=420)
        elif vista == "Links en columnas (MÁS RECOMENDADO)":
            st.dataframe(wide, use_container_width=True, height=420)
        else:
            st.dataframe(links_por_tienda, use_container_width=True, height=420)

        # (6) Descargar Excel con todas las vistas
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as xw:
            links_por_filas.to_excel(xw, index=False, sheet_name="links_por_filas")
            wide.to_excel(xw, index=False, sheet_name="links_en_columnas")
            links_por_tienda.to_excel(xw, index=False, sheet_name="links_por_tienda")
        st.download_button(
            "Descargar Excel (todas las vistas)",
            data=buf.getvalue(),
            file_name="links_por_tienda_formateado.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

# ------------------------------------------------------------
# MODO 2: === NUEVO === Comparar tiendas entre dos archivos
# ------------------------------------------------------------
elif modo.startswith("🧩"):
    st.title("Comparar tiendas entre dos archivos (CSV o Excel)")

    # Carga de archivos A y B (acepta .csv y .xlsx)
    c1, c2 = st.columns(2)
    with c1:
        upA = st.file_uploader("Archivo A (CSV/XLSX)", type=["csv", "xlsx"], key="cmp_A")
    with c2:
        upB = st.file_uploader("Archivo B (CSV/XLSX)", type=["csv", "xlsx"], key="cmp_B")

    if upA and upB:
        # Leer tablas y limpiar
        dfA, hojaA = leer_tabla(upA)
        dfB, hojaB = leer_tabla(upB)

        dfA = limpiar_df(dfA)
        dfB = limpiar_df(dfB)

        st.subheader("Vista previa")
        st.write("**Archivo A**", dfA.head())
        st.write("**Archivo B**", dfB.head())

        # Elegir columna TIENDA en cada archivo (por si el nombre no coincide)
        col_tienda_A = elegir_columna_tienda(dfA, key="cmp_tienda_A")
        col_tienda_B = elegir_columna_tienda(dfB, key="cmp_tienda_B")

        # Normalizar a una columna común llamada 'tienda'
        A = dfA[[col_tienda_A]].rename(columns={col_tienda_A: "tienda"})
        B = dfB[[col_tienda_B]].rename(columns={col_tienda_B: "tienda"})
        A = limpiar_df(A)
        B = limpiar_df(B)

        tiendas_A = set(A["tienda"])
        tiendas_B = set(B["tienda"])

        # Conjuntos resultado
        coinc = sorted(tiendas_A & tiendas_B)
        solo_A = sorted(tiendas_A - tiendas_B)  # Están en A, faltan en B
        solo_B = sorted(tiendas_B - tiendas_A)  # Están en B, faltan en A

        df_coinc = pd.DataFrame(coinc, columns=["tienda"])
        df_solo_A = pd.DataFrame(solo_A, columns=["tienda"])
        df_solo_B = pd.DataFrame(solo_B, columns=["tienda"])

        # KPIs rápidos
        k1, k2, k3 = st.columns(3)
        k1.metric("Coincidencias", len(df_coinc))
        k2.metric("Solo en A", len(df_solo_A))
        k3.metric("Solo en B", len(df_solo_B))

        with st.expander("Ver tablas"):
            st.write("**Coincidencias**", df_coinc)
            st.write("**Solo en A** (faltan en B)", df_solo_A)
            st.write("**Solo en B** (faltan en A)", df_solo_B)

        # (Opcional) Agregar links por tienda y comparativa lado a lado
        st.markdown("### (Opcional) Links por tienda")
        incluir_links = st.checkbox("Agregar hojas con links por tienda y una comparativa para coincidencias", value=True, key="cmp_links")

        dfs_out = {
            "Coincidencias": df_coinc,
            "Solo_en_A": df_solo_A,
            "Solo_en_B": df_solo_B,
        }

        if incluir_links:
            st.caption("Si tus archivos traen columnas link_* se usarán automático. Si no, elige una columna que contenga URLs (http/https).")

            # Detectar o elegir columnas de links en A
            link_cols_A = [c for c in dfA.columns if str(c).lower().startswith("link")]
            link_col_A = None
            if not link_cols_A:
                candidates_A = [c for c in dfA.columns if dfA[c].astype(str).str.contains("http", case=False, na=False).any()]
                if candidates_A:
                    link_col_A = st.selectbox("Columna LINK en A:", candidates_A, key="cmp_link_A")

            # Detectar o elegir columnas de links en B
            link_cols_B = [c for c in dfB.columns if str(c).lower().startswith("link")]
            link_col_B = None
            if not link_cols_B:
                candidates_B = [c for c in dfB.columns if dfB[c].astype(str).str.contains("http", case=False, na=False).any()]
                if candidates_B:
                    link_col_B = st.selectbox("Columna LINK en B:", candidates_B, key="cmp_link_B")

            # Construir tablas [tienda, links] para A y B
            def build_links(df_full, col_tienda_sel, link_cols, maybe_one_col):
                temp = df_full.copy()
                # Si no hay link_* pero se eligió una columna con URLs, usarla como 'link'
                if not link_cols and maybe_one_col:
                    link_cols = [maybe_one_col]
                if col_tienda_sel not in temp.columns:
                    return pd.DataFrame(columns=["tienda", "links"])
                # Mantener solo la columna tienda + columnas de link
                keep = [col_tienda_sel] + ([c for c in link_cols] if link_cols else [])
                temp = temp[keep].rename(columns={col_tienda_sel: "tienda"})
                temp = limpiar_df(temp)
                return agregar_links_por_tienda(temp)

            a_links = build_links(dfA, col_tienda_A, link_cols_A, link_col_A)
            b_links = build_links(dfB, col_tienda_B, link_cols_B, link_col_B)

            # Unir links por tienda solo para las coincidencias
            ambos = (
                df_coinc.merge(a_links, on="tienda", how="left")
                .rename(columns={"links": "links_A"})
                .merge(b_links, on="tienda", how="left")
                .rename(columns={"links": "links_B"})
            )

            # Convertir listas a texto multilínea (mejor lectura en Excel)
            for col in ["links_A", "links_B"]:
                if col in ambos.columns:
                    ambos[col] = ambos[col].apply(lambda x: "\n".join(x) if isinstance(x, list) else "")

            # Añadir hojas al Excel de salida
            dfs_out["A_links"] = a_links
            dfs_out["B_links"] = b_links
            dfs_out["Links_coincidencias"] = ambos

            # Vistas rápidas en pantalla
            with st.expander("Vistas de links"):
                st.write("**Links A**", a_links)
                st.write("**Links B**", b_links)
                st.write("**Links en coincidencias (lado a lado)**", ambos)

        # Descargar Excel final (comparación + links si aplica)
        binario = descargar_excel(dfs_out, "comparacion_tiendas.xlsx")
        st.download_button(
            "⬇️ Descargar Excel",
            data=binario,
            file_name="comparacion_tiendas.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
