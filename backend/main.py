import os
import uuid
import boto3
from boto3.dynamodb.conditions import Attr
from datetime import datetime
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from botocore.exceptions import ClientError
from botocore.config import Config
from dotenv import load_dotenv
import logging

# Cargar las variables secretas del archivo .env (AWS Academy Credentials)
load_dotenv()

# SEC-07: Configurar logging interno (nunca se expone al cliente)
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("archivacloud")

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

# Conexion segura a S3 adaptada para AWS Academy (Soporta Session Token dinamico)
# Se fuerza Signature V4 porque las credenciales temporales de voclabs no soportan V2
s3_client = boto3.client(
    "s3",
    region_name=REGION_NAME,
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    aws_session_token=os.getenv("AWS_SESSION_TOKEN"),
    config=Config(signature_version="s3v4"),
)

# Conexion a DynamoDB para registrar metadatos de archivos (Arquitectura Multi Cloud: S3 + DynamoDB)
DYNAMO_TABLE_NAME = "archivacloud-p09-files"
dynamodb_session = boto3.Session(
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    aws_session_token=os.getenv("AWS_SESSION_TOKEN"),
    region_name=REGION_NAME
)
dynamodb = dynamodb_session.resource("dynamodb")
dynamo_table = dynamodb.Table(DYNAMO_TABLE_NAME)

# Modelo Pydantic para validar los datos que envía el frontend (SEC-03)
class PresignedUrlRequest(BaseModel):
    fileName: str = Field(..., min_length=1, max_length=255)
    fileType: str
    fileSize: int

# Modelo Pydantic para validar la solicitud de descarga (SEC-03)
class DownloadUrlRequest(BaseModel):
    key: str = Field(..., min_length=1)

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
        
        logger.info(f"Presigned URL generada para subida: {object_key}")

        # Registrar metadatos del archivo en DynamoDB
        try:
            dynamo_table.put_item(
                Item={
                    "id_tabla": str(uuid.uuid4()),
                    "s3_key": object_key,
                    "nombre_original": request.fileName,
                    "tipo_archivo": request.fileType,
                    "tamano_bytes": request.fileSize,
                    "fecha_subida": datetime.utcnow().isoformat(),
                    "bucket": BUCKET_NAME
                }
            )
            logger.info(f"Metadatos registrados en DynamoDB para: {object_key}")
        except ClientError as dynamo_err:
            logger.error(f"Error al registrar en DynamoDB (no critico): {dynamo_err}")

        return {
            "presignedUrl": presigned_url,
            "key": object_key,
            "publicUrl": f"https://{BUCKET_NAME}.s3.{REGION_NAME}.amazonaws.com/{object_key}"
        }
        
    except ClientError as e:
        # SEC-07: Caja Negra - Log interno, mensaje generico al cliente
        logger.error(f"Error al generar presigned URL: {e}")
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

        logger.info(f"Listado de archivos: {len(archivos)} encontrados")
        return {"files": archivos}

    except ClientError as e:
        # SEC-07: Caja Negra
        logger.error(f"Error al listar archivos: {e}")
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
        s3_client.head_object(Bucket=BUCKET_NAME, Key=key)
        s3_client.delete_object(Bucket=BUCKET_NAME, Key=key)

        # Eliminar el registro correspondiente de DynamoDB
        try:
            response = dynamo_table.scan(
                FilterExpression=Attr("s3_key").eq(key)
            )
            for item in response.get("Items", []):
                dynamo_table.delete_item(Key={"id_tabla": item["id_tabla"]})
            logger.info(f"Registro eliminado de DynamoDB para: {key}")
        except ClientError as dynamo_err:
            logger.error(f"Error al eliminar de DynamoDB (no critico): {dynamo_err}")

        logger.info(f"Archivo eliminado de S3: {key}")
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

# CU-03 + CU-07 (Feature Extra P-09): Generar enlace temporal de descarga
# En vez de usar URL publica, se genera una presigned URL GET con TTL de 60 minutos
DOWNLOAD_TTL_SECONDS = 3600  # 60 minutos segun requisito del Anexo B para P-09

@app.post("/api/files/download-url")
async def generate_download_url(request: DownloadUrlRequest):
    key = request.key

    # SEC-03: Validar que el key sea de la carpeta uploads/
    if not key.startswith("uploads/"):
        raise HTTPException(
            status_code=400,
            detail="Solo se pueden descargar archivos dentro de la carpeta uploads/."
        )

    try:
        # Verificar que el archivo existe en el bucket
        s3_client.head_object(Bucket=BUCKET_NAME, Key=key)

        # Generar presigned URL de descarga con TTL de 60 minutos
        download_url = s3_client.generate_presigned_url(
            ClientMethod="get_object",
            Params={
                "Bucket": BUCKET_NAME,
                "Key": key
            },
            ExpiresIn=DOWNLOAD_TTL_SECONDS
        )

        logger.info(f"Enlace temporal de descarga generado para: {key} (TTL: {DOWNLOAD_TTL_SECONDS}s)")
        return {
            "downloadUrl": download_url,
            "expiresIn": DOWNLOAD_TTL_SECONDS,
            "message": f"Enlace temporal generado. Expira en 60 minutos."
        }

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
            detail="Error interno al generar el enlace de descarga."
        )

# Endpoint para consultar los metadatos de archivos registrados en DynamoDB
@app.get("/api/metadata")
async def get_metadata():
    try:
        response = dynamo_table.scan()
        registros = response.get("Items", [])
        # Convertir Decimal a int para que sea serializable en JSON
        for reg in registros:
            if "tamano_bytes" in reg:
                reg["tamano_bytes"] = int(reg["tamano_bytes"])
        logger.info(f"Consulta DynamoDB: {len(registros)} registros encontrados")
        return {"metadata": registros, "count": len(registros)}
    except ClientError as e:
        logger.error(f"Error al consultar DynamoDB: {e}")
        raise HTTPException(
            status_code=500,
            detail="Error interno al consultar el registro de metadatos."
        )

# Endpoint obligatorio de auditoria operativa / Health Check
@app.get("/healthz")
async def health_check():
    return {"status": "healthy", "services": ["s3", "dynamodb"]}