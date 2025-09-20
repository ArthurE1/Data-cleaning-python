from pathlib import Path
import pandas as pd
import re

# ==== CONFIGURA AQUÍ TU ARCHIVO ====
ENTRADA = Path(r"D:\PythonExcel\20250825_entregado_detergentes_linksd.xlsx")
HOJA = "Detalle"
COL_TIENDA = "tienda"
# Preferencia de columnas para links
PREFER_COLS = ["id_visita (URL extraída)", "link", "id_visita"]
ONE_PER_STORE = True   # True = además genera una hoja con 1 link por tienda
# ===================================

def autodetect_link_column(df: pd.DataFrame, prefer: list[str]) -> str:
    """Intenta detectar la mejor columna de link."""
    for c in prefer:
        if c in df.columns:
            return c
    url_re = re.compile(r'https?://', re.IGNORECASE)
    for c in df.columns:
        s = df[c].astype(str)
        if s.str.contains(url_re).any():
            return c
    raise ValueError("No encontré ninguna columna con links/URLs.")

def main():
    if not ENTRADA.exists():
        raise FileNotFoundError(f"No existe el archivo: {ENTRADA}")

    df = pd.read_excel(ENTRADA, sheet_name=HOJA)

    link_col = autodetect_link_column(df, PREFER_COLS)
    if COL_TIENDA not in df.columns:
        raise ValueError(f"No existe la columna de tienda '{COL_TIENDA}'. Columnas: {list(df.columns)}")

    base = df[[COL_TIENDA, link_col]].copy()
    base.columns = ["tienda", "link"]

    # Limpieza
    base = base.dropna(subset=["tienda", "link"])
    base["tienda"] = base["tienda"].astype(str).str.strip()
    base["link"]   = base["link"].astype(str).str.strip()
    base = base[base["link"] != ""]

    # Deduplicar
    pares_unicos = (
        base.drop_duplicates(subset=["tienda", "link"])
            .sort_values(["tienda", "link"])
            .reset_index(drop=True)
    )

    # Agrupar
    links_por_tienda = (
        pares_unicos.groupby("tienda")["link"]
        .agg(["nunique", lambda s: "\n".join(s.unique())])
        .reset_index()
        .rename(columns={"nunique": "links_unicos", "<lambda_0>": "links_unicos_list"})
        .sort_values("tienda")
    )

    # Resumen
    resumen = pd.DataFrame({
        "filas_originales": [len(df)],
        "pares_unicos": [len(pares_unicos)],
        "tiendas_con_al_menos_un_link": [links_por_tienda.shape[0]],
        "promedio_links_unicos_por_tienda": [
            round(links_por_tienda["links_unicos"].mean(), 2) if not links_por_tienda.empty else 0
        ],
        "columna_usada_para_link": [link_col],
        "columna_tienda": [COL_TIENDA]
    })

    # (Opcional) 1 link por tienda
    uno_por_tienda = None
    if ONE_PER_STORE:
        uno_por_tienda = (
            pares_unicos.sort_values(["tienda", "link"])
                        .groupby("tienda", as_index=False)
                        .first()
        )

    # Guardar
    salida = ENTRADA.with_name(ENTRADA.stem + "_dedup.xlsx")
    with pd.ExcelWriter(salida, engine="openpyxl") as xw:
        pares_unicos.to_excel(xw, index=False, sheet_name="pares_unicos")
        links_por_tienda.to_excel(xw, index=False, sheet_name="links_por_tienda")
        resumen.to_excel(xw, index=False, sheet_name="resumen")
        if uno_por_tienda is not None:
            uno_por_tienda.to_excel(xw, index=False, sheet_name="1link_por_tienda")

    print("==== OK ====")
    print(f"Entrada: {ENTRADA}")
    print(f"Usé columna de link: {link_col}")
    print(f"Salida: {salida}")

if __name__ == "__main__":
    main()
