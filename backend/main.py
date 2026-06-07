import os
import re
import uuid
import boto3
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from botocore.exceptions import ClientError
from botocore.config import Config
from dotenv import load_dotenv

# Cargar las variables secretas del archivo .env (AWS Academy Credentials)
load_dotenv()

app = FastAPI(title="ArchivaCloud - Portal P-09")

# SEC-02: Configuración de CORS restrictivo para permitir la comunicación nativa con React
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL, "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Parámetros únicos asignados a tu grupo P-09
BUCKET_NAME = "archivacloud-p09"  # Nombre de tu bucket
REGION_NAME = "us-east-1"        # Región obligatoria de tu laboratorio
ALLOWED_EXTENSIONS = {".png", ".svg"}
MAX_FILE_SIZE_BYTES = 6 * 1024 * 1024  # Límite estricto de pauta de 6 MB

# Conexión segura a S3 adaptada para AWS Academy (Soporta Session Token dinámico)
# Se fuerza Signature V4 porque las credenciales temporales de voclabs no soportan V2
s3_client = boto3.client(
    "s3",
    region_name=REGION_NAME,
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    aws_session_token=os.getenv("AWS_SESSION_TOKEN"),  # Requerido en entornos voclabs
    config=Config(signature_version="s3v4"),
)

# Modelo Pydantic para validar los datos que envía el frontend (SEC-03)
class PresignedUrlRequest(BaseModel):
    fileName: str = Field(..., min_length=1, max_length=255)
    fileType: str
    fileSize: int

def sanitizar_nombre_archivo(filename: str) -> str:
    """Genera un identificador único alfanumérico para evitar colisiones y errores de firma (SEC-03)"""
    _, ext = os.path.splitext(filename)
    # Crea un ID único limpio como 'a1b2c3d4-e5f6...' que jamás romperá la URL de S3
    id_unico = str(uuid.uuid4())
    return f"{id_unico}{ext.lower()}"

# CU-01: Endpoint para generar la URL de subida firmada (Flujo Desacoplado)
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
    ext = ext.lower()
    
    # Si por alguna razón el archivo no trae extensión en el nombre, la deducimos del MIME type (fileType)
    if not ext:
        if request.fileType == "image/png":
            ext = ".png"
        elif request.fileType == "image/svg+xml":
            ext = ".svg"
        filename_sanitizado += ext

    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Tipo de archivo no permitido. Detectado: '{ext}'. Solo se aceptan formatos PNG y SVG."
        )

    # Organizar el archivo dentro de la carpeta obligatoria uploads/
    object_key = f"uploads/{filename_sanitizado}"

    try:
        # Generar URL pre-firmada incluyendo ContentType para que la firma coincida
        # con el header Content-Type que envía el navegador al hacer PUT
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
        # SEC-07: Caja Negra - Ocultar trazas internas de error por seguridad
        raise HTTPException(
            status_code=500,
            detail="Error interno al procesar la solicitud con el almacenamiento cloud."
        )
# CU-02: Endpoint para listar los archivos del bucket bajo uploads/
@app.get("/api/files")
async def list_files():
    try:
        response = s3_client.list_objects_v2(
            Bucket=BUCKET_NAME,
            Prefix="uploads/"
        )

        archivos = []
        for obj in response.get("Contents", []):
            key = obj["Key"]
            # Saltar la carpeta uploads/ en sí misma
            if key == "uploads/":
                continue
            archivos.append({
                "key": key,
                "fileName": key.replace("uploads/", "", 1),
                "size": obj["Size"],
                "lastModified": obj["LastModified"].isoformat()
            })

        return {"files": archivos}

    except ClientError:
        # SEC-07: Caja Negra
        raise HTTPException(
            status_code=500,
            detail="Error interno al listar los archivos del almacenamiento cloud."
        )

# CU-04: Endpoint para eliminar un archivo del bucket
@app.delete("/api/files/{key:path}")
async def delete_file(key: str):
    # SEC-03: Validar que el key empiece con uploads/ para evitar eliminación arbitraria
    if not key.startswith("uploads/"):
        raise HTTPException(
            status_code=400,
            detail="Solo se pueden eliminar archivos dentro de la carpeta uploads/."
        )

    try:
        # Verificar que el objeto existe antes de eliminar
        s3_client.head_object(Bucket=BUCKET_NAME, Key=key)
        s3_client.delete_object(Bucket=BUCKET_NAME, Key=key)
        return {"message": f"Archivo '{key}' eliminado exitosamente."}

    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        if error_code == "404" or error_code == "NoSuchKey":
            raise HTTPException(
                status_code=404,
                detail="El archivo no fue encontrado en el almacenamiento cloud."
            )
        # SEC-07: Caja Negra
        raise HTTPException(
            status_code=500,
            detail="Error interno al eliminar el archivo del almacenamiento cloud."
        )

# Endpoint obligatorio de auditoría operativa / Health Check
@app.get("/healthz")
async def health_check():
    return {"status": "healthy"}