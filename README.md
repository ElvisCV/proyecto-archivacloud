# NOTAS DE PROGRESO - SPRINT 1

**Proyecto:** ArchivaCloud SpA (Portal de Carga Seguro)
**Estudiante:** Elvis Alejandro Candia Vargas (Trabajo Individual)
**Grupo:** P-09

---

## Restricciones del Grupo (P-09)
* Formatos permitidos: .png y .svg
* Peso máximo: 6 MB

---

## Controles de Seguridad Aplicados
* **SEC-01:** .gitignore configurado en la raíz para aislar claves (.env) y librerías (venv/).
* **SEC-02:** CORS bloqueado en FastAPI, solo permite peticiones desde http://localhost:5173.
* **SEC-03:** Sanitización de nombres de archivo con expresiones regulares (evita Path Traversal) y filtro duro de extensiones.
* **SEC-04:** Interceptor en backend para rechazar payloads mayores a 6 MB.
* **SEC-07:** Excepciones de AWS controladas con código HTTP 500 genérico (evita filtración de datos internos).

---

## Entorno Técnico
* Stack: Python, FastAPI, Uvicorn, Boto3 (AWS SDK).
* Región cloud utilizada: us-east-1
* Bucket asignado: archivacloud-p09

### Variables de configuración (.env.example)
```env
FRONTEND_URL=http://localhost:5173
AWS_ACCESS_KEY_ID=Clave_AWS_Aqui
AWS_SECRET_ACCESS_KEY=Secreto_AWS_Aqui
AWS_SESSION_TOKEN=Token_AWS_Aqui