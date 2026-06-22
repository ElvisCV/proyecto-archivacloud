# ArchivaCloud SpA -- Portal de Carga Seguro

**Codigo de pareja:** P-09  
**Integrante:** Elvis Alejandro Candia Vargas

---

## Parametros Unicos Respetados (Anexo B)

| Parametro | Valor |
|-----------|-------|
| Tipos de archivo permitidos | PNG, SVG |
| Tamano maximo | 6 MB |
| Nombre del bucket | archivacloud-p09 |
| Region | us-east-1 |
| Feature extra obligatoria | Enlace temporal de descarga (presigned URL con TTL de 60 min) |

---

## Arquitectura

El portal usa el patron de **presigned URLs**: el archivo se sube directamente desde el navegador a S3, sin pasar por el backend.

```
Browser (React)  --(1) POST /api/upload/presigned-url -->  FastAPI Backend
Browser (React)  <--(presignedUrl, key)--                  FastAPI Backend
Browser (React)  --(2) PUT presignedUrl --------------->   Amazon S3
```

Para descargas, se usa el mismo patron con URLs temporales de 60 minutos (feature extra P-09):

```
Browser (React)  --(1) POST /api/files/download-url -->  FastAPI Backend
Browser (React)  <--(downloadUrl, expiresIn)--           FastAPI Backend
Browser (React)  --(2) GET downloadUrl ----------------> Amazon S3
```

**Foto del diagrama manuscrito:** ver `docs/arquitectura.jpg`

---

## Stack y Versiones

| Componente | Tecnologia | Version |
|------------|-----------|---------|
| Backend | Python | 3.10+ |
| Framework API | FastAPI | ultima |
| Servidor ASGI | Uvicorn | ultima |
| AWS SDK | Boto3 | ultima |
| Validacion | Pydantic | v2 |
| Frontend | React | 19 |
| Bundler | Vite | 8 |
| HTTP Client | Axios | 1.17+ |
| Lenguaje Frontend | TypeScript | 6 |

---

## Variables de Entorno

| Variable | Descripcion | Ejemplo |
|----------|-------------|---------|
| `FRONTEND_URL` | URL del frontend para CORS | `http://localhost:5173` |
| `AWS_ACCESS_KEY_ID` | Clave de acceso de AWS Academy | `ASIAQUVCHP...` |
| `AWS_SECRET_ACCESS_KEY` | Clave secreta de AWS Academy | `TbJO+64CK7...` |
| `AWS_SESSION_TOKEN` | Token de sesion temporal de voclabs | `IQoJb3Jpz2...` |

---

## Politica IAM Minima

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

---

## Configuracion CORS del Bucket

```json
[
  {
    "AllowedHeaders": ["*"],
    "AllowedMethods": ["GET", "PUT", "DELETE", "HEAD"],
    "AllowedOrigins": ["http://localhost:5173", "http://127.0.0.1:5173"],
    "ExposeHeaders": ["ETag"],
    "MaxAgeSeconds": 3600
  }
]
```

---

## Endpoints de la API

| Metodo | Ruta | Descripcion |
|--------|------|-------------|
| POST | `/api/upload/presigned-url` | Genera presigned URL de subida |
| GET | `/api/files` | Lista archivos del bucket (nombre, tamano, fecha) |
| DELETE | `/api/files/{key}` | Elimina un archivo del bucket |
| POST | `/api/files/download-url` | Genera presigned URL de descarga (TTL 60 min) |
| GET | `/healthz` | Health check |

---

## Pasos para Correr el Proyecto

### Backend
```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
# Crear backend/.env con credenciales de AWS Academy (ver .env.example)
uvicorn main:app --reload
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

Abrir `http://localhost:5173` en el navegador.

---

## Escaneo de Dependencias (SEC-09)

### pip-audit (Backend)
```
No se encontraron vulnerabilidades conocidas.
```

### npm audit (Frontend)
```
found 0 vulnerabilities
```

---

## Feature Extra P-09: Enlace Temporal de Descarga

### Que hace
Genera un enlace temporal de descarga (presigned URL con TTL de 60 minutos) en vez de exponer URLs publicas del bucket S3.

### Por que este diseno
- **Seguridad:** Los archivos en S3 nunca son publicos. El bucket tiene Block Public Access activo.
- **Control de acceso:** Cada enlace expira en exactamente 60 minutos, evitando acceso indefinido.
- **Flujo:** El usuario hace clic en "Descargar", el frontend solicita al backend un enlace temporal, y el backend genera la presigned URL GET con `ExpiresIn=3600`.
- **Constante configurable:** `DOWNLOAD_TTL_SECONDS = 3600` permite ajustar el TTL facilmente.

---

## Controles de Seguridad (SEC-01 a SEC-10)

Ver detalle completo en `docs/reporte_seguridad.md`.

| ID | Control | Estado |
|----|---------|--------|
| SEC-01 | Secretos fuera del repo | Implementado |
| SEC-02 | CORS restrictivo | Implementado |
| SEC-03 | Validacion de entrada | Implementado |
| SEC-04 | Limite de tamano | Implementado |
| SEC-05 | IAM minimo privilegio | Implementado |
| SEC-06 | S3 cerrado al publico | Implementado |
| SEC-07 | Errores sin info sensible | Implementado |
| SEC-08 | Encriptacion en reposo | Implementado |
| SEC-09 | Escaneo de dependencias | Implementado |
| SEC-10 | TLS de extremo a extremo | Implementado |

---

## Notas de Progreso

### Sprint 1 -- Setup + Backend Minimo
- Repositorio Git creado y compartido en GitHub.
- Bucket S3 `archivacloud-p09` creado en `us-east-1`.
- Endpoint `POST /api/upload/presigned-url` funcionando.
- Endpoint `GET /healthz` de auditoria operativa.
- Firma S3 configurada con Signature V4 para credenciales temporales.

### Sprint 2 -- Backend Completo + Frontend Base
- Endpoints `GET /api/files` y `DELETE /api/files/{key}` implementados.
- Frontend SPA con subida, listado y eliminacion de archivos.
- Barra de progreso visible durante la subida.
- Refresco automatico de la lista al subir o eliminar.

### Sprint 3 -- Feature Extra + Seguridad
- Feature extra P-09 implementada: presigned URL de descarga con TTL 60 min.
- Controles SEC-01 a SEC-10 implementados y documentados.
- Reporte de seguridad creado en `docs/reporte_seguridad.md`.

### Sprint 4 -- Documentacion + Defensa
- README final completo segun Anexo D.
- Tag `v1.0.0` creado.

---

## Autor

**Elvis Alejandro Candia Vargas**  
Carrera: Ingenieria Informatica  
Asignatura: Arquitectura Multi Cloud