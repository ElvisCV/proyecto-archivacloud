import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';

// Obtención de la URL base desde las variables de entorno de Vite
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// Restricciones duras asignadas al Grupo P-09
const MAX_FILE_SIZE_BYTES = 6 * 1024 * 1024; // Límite estricto de pauta: 6 MB
const ALLOWED_EXTENSIONS = ['png', 'svg'];
const ALLOWED_MIME_TYPES = ['image/png', 'image/svg+xml'];

// Interfaz para los archivos que devuelve el backend
interface ArchivoS3 {
  key: string;
  fileName: string;
  size: number;
  lastModified: string;
}

// Función para formatear bytes a unidades legibles
function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// Función para formatear fecha
function formatDate(isoString: string): string {
  const date = new Date(isoString);
  return date.toLocaleDateString('es-CL', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  });
}

export default function App() {
  const [file, setFile] = useState<File | null>(null);
  const [status, setStatus] = useState<string>('');
  const [error, setError] = useState<string>('');
  const [isUploading, setIsUploading] = useState<boolean>(false);
  const [archivos, setArchivos] = useState<ArchivoS3[]>([]);
  const [loadingFiles, setLoadingFiles] = useState<boolean>(false);
  const [deletingKey, setDeletingKey] = useState<string | null>(null);
  const [downloadingKey, setDownloadingKey] = useState<string | null>(null);
  const [uploadProgress, setUploadProgress] = useState<number>(0);

  // CU-02: Cargar la lista de archivos desde el backend
  const fetchArchivos = useCallback(async () => {
    setLoadingFiles(true);
    try {
      const response = await axios.get(`${API_BASE_URL}/api/files`);
      setArchivos(response.data.files);
    } catch (err) {
      console.error('Error al listar archivos:', err);
    } finally {
      setLoadingFiles(false);
    }
  }, []);

  // Cargar archivos al montar el componente
  useEffect(() => {
    fetchArchivos();
  }, [fetchArchivos]);

  // Manejo del cambio de archivo con controles de ciberseguridad en cliente
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setError('');
    setStatus('');
    
    if (!e.target.files || e.target.files.length === 0) return;

    const selectedFile = e.target.files[0];
    const fileExtension = selectedFile.name.split('.').pop()?.toLowerCase() || '';

    // Control de Extensión (Client-side validation - SEC-03)
    if (!ALLOWED_EXTENSIONS.includes(fileExtension) || !ALLOWED_MIME_TYPES.includes(selectedFile.type)) {
      setError(`Error: Formato no permitido. Solo se admiten archivos .png y .svg (Grupo P-09)`);
      setFile(null);
      return;
    }

    // Control de Tamaño Payload (Client-side validation - SEC-04)
    if (selectedFile.size > MAX_FILE_SIZE_BYTES) {
      setError(`Error: El archivo excede el límite estricto de 6 MB.`);
      setFile(null);
      return;
    }

    setFile(selectedFile);
    setStatus('Archivo seleccionado y validado localmente de forma segura.');
  };

  // CU-01: Flujo de carga desacoplado en dos pasos
  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) {
      setError('Por favor, seleccione un archivo válido.');
      return;
    }

    setIsUploading(true);
    setError('');
    setStatus('Paso 1: Solicitando URL pre-firmada al backend...');

    try {
      // 1. OBTENCIÓN DE URL PRE-FIRMADA (POST hacia FastAPI)
      const presignedResponse = await axios.post(`${API_BASE_URL}/api/upload/presigned-url`, {
        fileName: file.name,
        fileSize: file.size,
        fileType: file.type
      });

      const { presignedUrl } = presignedResponse.data;
      
      setStatus('Paso 2: Transfiriendo archivo binario directamente a Amazon S3 mediante PUT...');
      setUploadProgress(0);

      // 2. ENVÍO DIRECTO AL BUCKET DE S3 (PUT con Content-Type y barra de progreso)
      await axios.put(presignedUrl, file, {
        headers: {
          'Content-Type': file.type
        },
        onUploadProgress: (progressEvent) => {
          if (progressEvent.total) {
            const percent = Math.round((progressEvent.loaded * 100) / progressEvent.total);
            setUploadProgress(percent);
          }
        }
      });

      setUploadProgress(100);
      setStatus(`Carga completada de forma segura en la nube: ${file.name}`);
      setFile(null);

      // Refrescar la lista automáticamente después de subir
      await fetchArchivos();

    } catch (err: any) {
      console.error(err);
      // CU-06: Manejo de errores sin trazas técnicas
      if (err.response?.data?.detail) {
        setError(err.response.data.detail);
      } else {
        setError('Error en el proceso de carga. Verifique la vigencia de las credenciales de AWS.');
      }
      setStatus('');
    } finally {
      setIsUploading(false);
      setUploadProgress(0);
    }
  };

  // CU-03 + CU-07 (Feature Extra P-09): Descargar archivo con enlace temporal
  const handleDownload = async (key: string, fileName: string) => {
    setDownloadingKey(key);
    setError('');

    try {
      const response = await axios.post(`${API_BASE_URL}/api/files/download-url`, { key });
      const { downloadUrl } = response.data;
      // Abrir el enlace temporal en una nueva pestaña
      window.open(downloadUrl, '_blank');
      setStatus(`Enlace temporal generado para "${fileName}". Expira en 60 minutos.`);
    } catch (err: any) {
      console.error(err);
      if (err.response?.data?.detail) {
        setError(err.response.data.detail);
      } else {
        setError('Error al generar el enlace de descarga.');
      }
    } finally {
      setDownloadingKey(null);
    }
  };

  // CU-04: Eliminar archivo con confirmación
  const handleDelete = async (key: string, fileName: string) => {
    const confirmar = window.confirm(
      `¿Está seguro de eliminar "${fileName}"?\nEsta acción es irreversible.`
    );
    if (!confirmar) return;

    setDeletingKey(key);
    setError('');

    try {
      await axios.delete(`${API_BASE_URL}/api/files/${key}`);
      setStatus(`Archivo "${fileName}" eliminado exitosamente.`);
      await fetchArchivos();
    } catch (err: any) {
      console.error(err);
      if (err.response?.data?.detail) {
        setError(err.response.data.detail);
      } else {
        setError('Error al eliminar el archivo. Intente nuevamente.');
      }
    } finally {
      setDeletingKey(null);
    }
  };

  return (
    <div style={{ fontFamily: 'sans-serif', maxWidth: '800px', margin: '40px auto', padding: '20px' }}>
      {/* Encabezado */}
      <div style={{ border: '1px solid #ccc', borderRadius: '8px', padding: '20px', boxShadow: '0 2px 4px rgba(0,0,0,0.1)', marginBottom: '20px' }}>
        <h2 style={{ color: '#0070c0', margin: '0 0 4px' }}>ArchivaCloud SpA - Portal de Carga Seguro (P-09)</h2>
        <p style={{ fontSize: '14px', color: '#666', margin: 0 }}>Desarrollo Frontend e Integración - Sprint 3</p>
        
        <form onSubmit={handleUpload} style={{ display: 'flex', flexDirection: 'column', gap: '15px', marginTop: '20px' }}>
          <label style={{ fontWeight: 'bold', color: '#333' }}>Seleccione el archivo a subir (.png o .svg, máx. 6MB):</label>
          <input 
            type="file" 
            accept=".png,.svg" 
            onChange={handleFileChange} 
            disabled={isUploading}
            style={{ padding: '10px', border: '1px dashed #bbb', borderRadius: '4px', backgroundColor: '#fafafa' }}
          />

          {status && <div style={{ padding: '10px', backgroundColor: '#e2f0d9', color: '#385723', borderRadius: '4px', fontSize: '14px', borderLeft: '4px solid #385723' }}>{status}</div>}
          {error && <div style={{ padding: '10px', backgroundColor: '#fce4d6', color: '#c65911', borderRadius: '4px', fontSize: '14px', borderLeft: '4px solid #c65911' }}>{error}</div>}

          {/* CU-01: Barra de progreso visible durante la subida */}
          {isUploading && (
            <div style={{ width: '100%', backgroundColor: '#e0e0e0', borderRadius: '4px', overflow: 'hidden' }}>
              <div
                style={{
                  width: `${uploadProgress}%`,
                  height: '24px',
                  backgroundColor: uploadProgress === 100 ? '#28a745' : '#0070c0',
                  transition: 'width 0.3s ease',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: 'white',
                  fontSize: '12px',
                  fontWeight: 'bold'
                }}
              >
                {uploadProgress}%
              </div>
            </div>
          )}

          <button 
            type="submit" 
            disabled={!file || isUploading}
            style={{ padding: '12px', backgroundColor: !file || isUploading ? '#ccc' : '#0070c0', color: 'white', border: 'none', borderRadius: '4px', cursor: !file || isUploading ? 'not-allowed' : 'pointer', fontWeight: 'bold', transition: 'background-color 0.2s' }}
          >
            {isUploading ? 'Procesando carga en la nube...' : 'Iniciar Carga Segura'}
          </button>
        </form>
      </div>

      {/* CU-02: Lista de archivos */}
      <div style={{ border: '1px solid #ccc', borderRadius: '8px', padding: '20px', boxShadow: '0 2px 4px rgba(0,0,0,0.1)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '15px' }}>
          <h3 style={{ color: '#333', margin: 0 }}>
            Archivos en el Bucket
            {archivos.length > 0 && (
              <span style={{ marginLeft: '8px', fontSize: '13px', color: '#666', fontWeight: 'normal' }}>({archivos.length} archivo{archivos.length !== 1 ? 's' : ''})</span>
            )}
          </h3>
          <button 
            onClick={fetchArchivos} 
            disabled={loadingFiles}
            style={{ padding: '6px 14px', backgroundColor: '#f0f0f0', border: '1px solid #ccc', borderRadius: '4px', cursor: 'pointer', fontSize: '13px' }}
          >
            {loadingFiles ? 'Cargando...' : '↻ Refrescar'}
          </button>
        </div>

        {archivos.length === 0 ? (
          <p style={{ fontSize: '14px', color: '#999', textAlign: 'center', padding: '20px 0' }}>
            {loadingFiles ? 'Cargando archivos...' : 'No hay archivos en el bucket.'}
          </p>
        ) : (
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '14px' }}>
            <thead>
              <tr style={{ backgroundColor: '#f5f5f5', textAlign: 'left' }}>
                <th style={{ padding: '10px', borderBottom: '2px solid #ddd' }}>Nombre</th>
                <th style={{ padding: '10px', borderBottom: '2px solid #ddd' }}>Tamaño</th>
                <th style={{ padding: '10px', borderBottom: '2px solid #ddd' }}>Fecha</th>
                <th style={{ padding: '10px', borderBottom: '2px solid #ddd', textAlign: 'center' }}>Acciones</th>
              </tr>
            </thead>
            <tbody>
              {archivos.map((archivo) => (
                <tr key={archivo.key} style={{ borderBottom: '1px solid #eee' }}>
                  <td style={{ padding: '10px', color: '#333', wordBreak: 'break-all' }}>{archivo.fileName}</td>
                  <td style={{ padding: '10px', color: '#666' }}>{formatBytes(archivo.size)}</td>
                  <td style={{ padding: '10px', color: '#666' }}>{formatDate(archivo.lastModified)}</td>
                  <td style={{ padding: '10px', textAlign: 'center' }}>
                    <button
                      onClick={() => handleDownload(archivo.key, archivo.fileName)}
                      disabled={downloadingKey === archivo.key}
                      style={{
                        padding: '5px 12px',
                        backgroundColor: downloadingKey === archivo.key ? '#ccc' : '#28a745',
                        color: 'white',
                        border: 'none',
                        borderRadius: '4px',
                        cursor: downloadingKey === archivo.key ? 'not-allowed' : 'pointer',
                        fontSize: '13px',
                        marginRight: '6px'
                      }}
                    >
                      {downloadingKey === archivo.key ? 'Generando...' : 'Descargar'}
                    </button>
                    <button
                      onClick={() => handleDelete(archivo.key, archivo.fileName)}
                      disabled={deletingKey === archivo.key}
                      style={{
                        padding: '5px 12px',
                        backgroundColor: deletingKey === archivo.key ? '#ccc' : '#dc3545',
                        color: 'white',
                        border: 'none',
                        borderRadius: '4px',
                        cursor: deletingKey === archivo.key ? 'not-allowed' : 'pointer',
                        fontSize: '13px'
                      }}
                    >
                      {deletingKey === archivo.key ? 'Eliminando...' : 'Eliminar'}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Pie de pagina */}
      <div style={{ marginTop: '20px', padding: '15px', textAlign: 'center', fontSize: '12px', color: '#999', borderTop: '1px solid #eee' }}>
        <p style={{ margin: '0 0 4px' }}>ArchivaCloud SpA - Grupo P-09 | Los enlaces de descarga expiran en 60 minutos</p>
        <p style={{ margin: 0 }}>Formatos permitidos: PNG, SVG | Tamano maximo: 6 MB</p>
      </div>
    </div>
  );
}