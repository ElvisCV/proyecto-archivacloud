# Frontend - ArchivaCloud SpA (P-09)

SPA desarrollada en React 19 + Vite + TypeScript para el portal de carga seguro.

## Requisitos

- Node.js 18+
- npm 9+

## Instalacion

```bash
npm install
```

## Desarrollo

```bash
npm run dev
```

El servidor de desarrollo se abre en `http://localhost:5173`.

## Variables de entorno

Copiar `.env.example` a `.env` y ajustar si es necesario:

```env
VITE_API_URL=http://localhost:8000
```

## Funcionalidades

- Subida de archivos PNG y SVG (max 6 MB) con barra de progreso
- Listado de archivos con nombre, tamano y fecha
- Descarga mediante enlace temporal (presigned URL, 60 min TTL)
- Eliminacion de archivos con confirmacion
- Validacion de tipo y tamano en cliente (SEC-03, SEC-04)
- Manejo de errores sin trazas tecnicas (SEC-07)
