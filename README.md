# 🚀 Dashboard NASA con Streamlit

Dashboard interactivo que consume la API abierta de NASA (https://api.nasa.gov/):

- **APOD**: imagen/video astronómico del día
- **NeoWs**: asteroides cercanos a la Tierra (métricas y gráficas)
- **DONKI**: erupciones solares recientes

## Configuración (Windows / PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### API key (no se sube a GitHub)

Copia el ejemplo y pega tu clave (obtenla gratis en https://api.nasa.gov/):

```powershell
copy .env.example .env
# edita .env y reemplaza tu_clave_aqui
```

`.env` y `.streamlit/secrets.toml` están en `.gitignore`.

## Ejecutar

```powershell
streamlit run app.py
```

## Despliegue en Streamlit Community Cloud

En *Settings → Secrets* agrega:

```toml
NASA_API_KEY = "tu_clave_aqui"
```
