\# Data Cleaning \& App Links (Python + Streamlit)



Este repositorio contiene scripts en \*\*Python\*\* y una aplicación en \*\*Streamlit\*\* para:

\- Limpiar y deduplicar pares de tiendas y links a partir de archivos Excel/CSV.

\- Comparar dos archivos de tiendas para identificar coincidencias y diferencias.

\- Exportar los resultados en distintos formatos a Excel.



\## 🚀 Tecnologías utilizadas

\- Python 3.10

\- Pandas

\- Openpyxl

\- Streamlit



\## 📂 Estructura del repositorio

\- `app\_links.py` → aplicación principal en Streamlit.

\- `dedup\_por\_tienda.py` → módulo auxiliar para depuración por tienda.

\- `extraer\_tienda\_links.py` → módulo auxiliar para extracción de links.

\- `requirements.txt` → dependencias necesarias.



\## ⚙️ Instalación

Clona este repositorio y crea un entorno virtual:



```bash

git clone https://github.com/ArthurE1/data-cleaning-python.git

cd data-cleaning-python

python -m venv .venv

.\\.venv\\Scripts\\activate

pip install -r requirements.txt



