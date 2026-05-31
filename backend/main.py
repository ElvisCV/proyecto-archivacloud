import os
import re
import boto3
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from botocore.exceptions import ClientError
from dotenv import load_dotenv

# Cargar las variables secretas del archivo .env
load_dotenv()

app = FastAPI(title="ArchivaCloud - Portal P-09")

# SEC-02: CORS restrictivo apuntando a tu futuro React
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Parámetros únicos asignados a tu grupo P-09
BUCKET_NAME = "archivacloud-p09"  # Nombre de tu bucket
REGION_NAME = "us-east-1"        # Región obligatoria de tu fila
ALLOWED_EXTENSIONS = {".png", ".svg"}
MAX_FILE_SIZE_BYTES = 6 * 1024 * 1024  # Límite estricto de 6 MB

# Conexión segura a S3 adaptada para AWS Academy (Soporta Session Token)
s3_client = boto3.client(
    "s3",
    region_name=REGION_NAME,
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    aws_session_token=os.getenv("AWS_SESSION_TOKEN"),  # Requerido en entornos académicos voclabs
)

# Modelo Pydantic para validar los datos que envía el frontend (SEC-03)
class PresignedUrlRequest(BaseModel):
    fileName: str = Field(..., min_length=1, max_length=255)
    fileType: str
    fileSize: int

def sanitizar_nombre_archivo(filename: str) -> str:
    """Evita inyecciones de ruta o caracteres extraños en AWS (SEC-03)"""
    name, ext = os.path.splitext(filename)
    name = re.sub(r'[^a-zA-Z0-9_\-]', '_', name)
    return f"{name}{ext.lower()}"

# CU-01: Endpoint para generar la URL de subida firmada
@app.post("/api/upload/presigned-url")
async def generate_upload_url(request: PresignedUrlRequest):
    # SEC-04: Validar límite de tamaño de 6 MB antes de ir a AWS
    if request.fileSize > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=400,
            detail="El archivo excede el tamaño máximo permitido de 6 MB."
        )

    # SEC-03: Validar extensiones permitidas para el grupo P-09
    filename_sanitizado = sanitizar_nombre_archivo(request.fileName)
    _, ext = os.path.splitext(filename_sanitizado)
    
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="Tipo de archivo no permitido. Solo se aceptan PNG y SVG."
        )

    # Organizar el archivo dentro de la carpeta obligatoria uploads/
    object_key = f"uploads/{filename_sanitizado}"

    try:
        # Pedirle a AWS S3 la URL firmada para que el cliente suba directo
        presigned_url = s3_client.generate_presigned_url(
            ClientMethod="put_object",
            Params={
                "Bucket": BUCKET_NAME,
                "Key": object_key,
                "ContentType": request.fileType
            },
            ExpiresIn=900  # Expira en 15 minutos
        )
        
        return {
            "presignedUrl": presigned_url,
            "key": object_key,
            "publicUrl": f"https://{BUCKET_NAME}.s3.{REGION_NAME}.amazonaws.com/{object_key}"
        }
        
    except ClientError:
        # SEC-07: Ocultar trazas internas de error por seguridad
        raise HTTPException(
            status_code=500,
            detail="Error interno al procesar la solicitud con el almacenamiento cloud."
        )

# Endpoint obligatorio de Health Check
@app.get("/healthz")
async def health_check():
    return {"status": "healthy"}