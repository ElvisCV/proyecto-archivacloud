# Reporte de Seguridad — ArchivaCloud SpA (P-09)

**Proyecto:** ArchivaCloud SpA  
**Grupo:** P-09  
**Estudiante:** Elvis Alejandro Candia Vargas

---

## Resumen de Controles SEC-01 a SEC-10

### SEC-01: Secretos fuera del repositorio
- El archivo `.env` del backend contiene las credenciales de AWS y esta incluido en `.gitignore`.
- Se provee un archivo `.env.example` con placeholders para facilitar la configuracion sin exponer datos reales.
- El historial de Git no contiene credenciales.

### SEC-02: CORS restrictivo
- La configuracion de CORS en FastAPI (`CORSMiddleware`) solo permite origenes especificos:
  - `http://localhost:5173`
  - `http://127.0.0.1:5173`
- No se usa el comodin `*` en `allow_origins`.

### SEC-03: Validacion de entrada
- Se utiliza Pydantic (`PresignedUrlRequest`) para validar los campos `fileName`, `fileType` y `fileSize`.
- Los nombres de archivo se sanitizan reemplazandolos por UUID v4, lo que previene ataques de Path Traversal.
- Se aplica una lista blanca de extensiones permitidas: unicamente `.png` y `.svg` (parametros del grupo P-09).
- En el endpoint DELETE se valida que el `key` comience con `uploads/` para evitar eliminacion arbitraria.

### SEC-04: Limite de tamano
- El frontend valida que el archivo no exceda 6 MB antes de enviarlo al backend.
- El backend valida nuevamente el campo `fileSize` contra `MAX_FILE_SIZE_BYTES = 6 * 1024 * 1024`.
- Doble validacion (cliente + servidor) asegura que no se acepten archivos fuera de limite.

### SEC-05: IAM de minimo privilegio
- La politica IAM del usuario asociado al bucket `archivacloud-p09` incluye unicamente las acciones necesarias:
  - `s3:PutObject` — para subir archivos
  - `s3:GetObject` — para descargar archivos
  - `s3:DeleteObject` — para eliminar archivos
  - `s3:ListBucket` — para listar el contenido
- No se usan comodines en el recurso ARN; se especifica el bucket exacto.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject",
        "s3:DeleteObject"
      ],
      "Resource": "arn:aws:s3:::archivacloud-p09/*"
    },
    {
      "Effect": "Allow",
      "Action": "s3:ListBucket",
      "Resource": "arn:aws:s3:::archivacloud-p09"
    }
  ]
}
```

### SEC-06: S3 cerrado al publico
- Block Public Access esta activo en el bucket `archivacloud-p09`.
- No existe una Bucket Policy permisiva.
- Los archivos solo son accesibles mediante presigned URLs temporales generadas por el backend.

### SEC-07: Errores sin informacion sensible
- Todas las excepciones de AWS (`ClientError`) se capturan y se devuelven como HTTP 500 con un mensaje generico.
- No se exponen stack traces, ARNs ni datos internos al cliente.
- Los errores de validacion (extensiones, tamano) devuelven HTTP 400 con mensajes claros pero sin informacion tecnica interna.

### SEC-08: Encriptacion en reposo
- El bucket `archivacloud-p09` tiene SSE-S3 (Server-Side Encryption con claves administradas por S3) activado.
- Todos los objetos subidos son encriptados automaticamente en reposo.

### SEC-09: Escaneo de dependencias
- Se ejecuto `pip-audit` en el backend para verificar vulnerabilidades en dependencias de Python.
- Se ejecuto `npm audit` en el frontend para verificar vulnerabilidades en dependencias de Node.js.
- Los resultados se documentan en la seccion correspondiente del README.
- Las vulnerabilidades High/Critical fueron mitigadas o justificadas.

### SEC-10: TLS de extremo a extremo
- Todas las llamadas del backend a S3 se realizan sobre HTTPS (protocolo por defecto de boto3).
- Las presigned URLs generadas utilizan el esquema `https://`.
- En desarrollo local, la comunicacion frontend-backend es HTTP (localhost). En produccion, se configuraria un reverse proxy (nginx) con certificado TLS/SSL.
