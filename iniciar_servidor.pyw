import uvicorn
import os

if __name__ == "__main__":
    # Cambiar al directorio actual del script por seguridad
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    # Iniciar FastAPI en el puerto 8000 accesible por la red local
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)