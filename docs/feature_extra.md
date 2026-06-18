# Feature Extra P-09: Enlace Temporal de Descarga

## Descripcion

El grupo P-09 tiene como feature extra obligatoria la generacion de un enlace temporal de descarga utilizando presigned URLs con un TTL (Time To Live) de 60 minutos, en vez de exponer URLs publicas del bucket S3.

## Como funciona

1. El usuario hace clic en el boton "Descargar" en la tabla de archivos.
2. El frontend envia un `POST /api/files/download-url` al backend con el `key` del archivo.
3. El backend valida que el key pertenezca a la carpeta `uploads/` y verifica que el archivo exista.
4. Se genera una presigned URL de tipo GET con `ExpiresIn=3600` (60 minutos).
5. El frontend recibe la URL y la abre en una nueva pestana del navegador.

## Diagrama del flujo

```
Usuario                Frontend (React)           Backend (FastAPI)          Amazon S3
  |                         |                           |                       |
  |-- Clic "Descargar" -->  |                           |                       |
  |                         |-- POST /download-url -->  |                       |
  |                         |                           |-- head_object ------> |
  |                         |                           |<-- 200 OK ----------- |
  |                         |                           |-- generate_presigned  |
  |                         |<-- { downloadUrl } -------|   (GET, 3600s)        |
  |<-- window.open(url) --- |                           |                       |
  |                         |                           |                       |
  |------- GET url ---------|---------------------------|---------------------> |
  |<------ Archivo ---------|---------------------------|---------------------- |
```

## Por que este diseno

- **Seguridad:** El bucket tiene Block Public Access activo. Los archivos nunca son accesibles publicamente.
- **Control de acceso temporal:** Cada enlace expira exactamente en 60 minutos, evitando acceso indefinido.
- **Auditoria:** El backend puede loggear cada solicitud de descarga sin exponer informacion al cliente.
- **Configurable:** La constante `DOWNLOAD_TTL_SECONDS = 3600` se puede ajustar facilmente.

## Endpoint

| Metodo | Ruta | Body | Respuesta |
|--------|------|------|-----------|
| POST | `/api/files/download-url` | `{ "key": "uploads/archivo.png" }` | `{ "downloadUrl": "https://...", "expiresIn": 3600 }` |

## Validaciones aplicadas

- El campo `key` se valida con Pydantic (modelo `DownloadUrlRequest`).
- Se verifica que el key comience con `uploads/` para prevenir acceso a otros prefijos.
- Se verifica que el archivo exista con `head_object` antes de generar la URL.
- Los errores se manejan sin exponer trazas internas (SEC-07).
