# NOTAS DE PROGRESO — ArchivaCloud SpA (P-09)

**Proyecto:** ArchivaCloud SpA (Portal de Carga Seguro)
**Estudiante:** Elvis Alejandro Candia Vargas (Trabajo Individual)
**Grupo:** P-09

---

## Restricciones del Grupo (P-09)
* Formatos permitidos: .png y .svg
* Peso máximo: 6 MB
* Bucket: archivacloud-p09
* Región: us-east-1

---

## Entorno Técnico
* **Backend:** Python 3.10+, FastAPI, Uvicorn, Boto3 (AWS SDK), Pydantic, python-dotenv
* **Frontend:** React 19 + Vite + Axios + TypeScript
* Región cloud utilizada: us-east-1
* Bucket asignado: archivacloud-p09

### Variables de configuración (.env.example)
```env
FRONTEND_URL=http://localhost:5173
AWS_ACCESS_KEY_ID=Clave_AWS_Aqui
AWS_SECRET_ACCESS_KEY=Secreto_AWS_Aqui
AWS_SESSION_TOKEN=Token_AWS_Aqui
```

---

## Sprint 1 — Setup + Backend Mínimo ✅

### Logros
* Repositorio Git creado y compartido en GitHub.
* Bucket S3 `archivacloud-p09` creado en `us-east-1`.
* Usuario IAM configurado con credenciales temporales de AWS Academy.
* Endpoint `POST /api/upload/presigned-url` funcionando: genera presigned URL para subida directa a S3.
* Endpoint `GET /healthz` de auditoría operativa.
* Firma S3 configurada con **Signature V4** (`s3v4`) para compatibilidad con credenciales temporales de voclabs.

### Controles de Seguridad Aplicados (Sprint 1)
* **SEC-01:** `.gitignore` configurado para aislar `backend/.env`, `venv/`, `__pycache__/`, `frontend/.env`.
* **SEC-02:** CORS restrictivo en FastAPI, solo permite peticiones desde `http://localhost:5173` y `http://127.0.0.1:5173`.
* **SEC-03:** Sanitización de nombres de archivo con UUID v4 (evita colisiones y Path Traversal) + lista blanca de extensiones (.png, .svg).
* **SEC-04:** Validación de tamaño máximo (6 MB) tanto en frontend como en backend.
* **SEC-07:** Excepciones de AWS controladas con código HTTP 500 genérico (evita filtración de datos internos).

---

## Sprint 2 — Backend Completo + Frontend Base ✅

### Logros
* Endpoint `GET /api/files` implementado: lista objetos del bucket bajo `uploads/` con nombre, tamaño y fecha.
* Endpoint `DELETE /api/files/{key}` implementado: elimina archivos con validación de prefijo `uploads/`.
* Frontend SPA en React + Vite + TypeScript completamente funcional:
  - Formulario de subida con validación de extensión y tamaño en cliente.
  - Tabla de archivos con nombre, tamaño formateado y fecha.
  - Botón de eliminar con `window.confirm` (acción irreversible).
  - Refresco automático de la lista al subir o eliminar.
  - Botón manual de refresco.
* Firma de presigned URL corregida: se incluye `ContentType` en los parámetros de firma para que coincida con el header `Content-Type` enviado por Axios.

### Endpoints disponibles (Sprint 2)
| Método | Ruta | Descripción |
|--------|------|-------------|
| POST | `/api/upload/presigned-url` | Genera presigned URL de subida |
| GET | `/api/files` | Lista archivos del bucket |
| DELETE | `/api/files/{key}` | Elimina un archivo del bucket |
| GET | `/healthz` | Health check |

### Cómo correr el proyecto
**Backend:**
```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
# Crear backend/.env con credenciales de AWS Academy
uvicorn main:app --reload
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```
Abrir `http://localhost:5173` en el navegador.

---

## Próximos pasos (Sprint 3)
* Implementar feature extra P-09: enlace temporal de descarga (presigned URL con TTL de 60 min).
* Completar controles SEC-05 a SEC-10.
* Diagrama de arquitectura manuscrito.