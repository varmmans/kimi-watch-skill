---
name: watch
description: Ver y analizar videos de YouTube o de cualquier sitio de internet. Extrae la transcripción, los puntos principales, los métodos/herramientas mostrados y los elementos accionables para automatizar el trabajo del usuario. Usar cuando el usuario pida "ver", analizar, resumir o extraer la transcripción de un video (de YouTube, Vimeo, TikTok, cursos, webinars, etc.), especialmente con intención de aprovechar el contenido para automatizar su trabajo. Soporta los parámetros --transcript (transcripción completa en .txt/.md), --md (análisis en formato Markdown), --file (guardar el resultado como archivo descargable) y --lang (idioma preferido de subtítulos).
---

# watch — Analizar videos para extraer conocimiento accionable

## Uso

```
watch <url-del-video> [--transcript] [--md] [--file] [--lang <código>]
```

Parámetros:

- `--transcript`: extrae la transcripción completa y entrégala como archivo `.txt` (o `.md` si se combina con `--md`) con marcas de tiempo `[HH:MM:SS]`. No hace análisis salvo que se pida explícitamente.
- `--md`: el análisis se entrega formateado en Markdown (encabezados, listas, tabla de herramientas).
- `--file`: además de mostrar el resultado, guárdalo como archivo descargable en `/mnt/agents/output/` (`.md` para análisis, `.txt` para transcripción). Sin este parámetro el resultado se muestra solo en el chat.
- `--lang <código>`: idioma preferido de subtítulos (p. ej. `es`, `en`). Si no existe, usar el disponible.

## Flujo de trabajo

### 1. Obtener la transcripción

Ejecutar el script de extracción (estrategia automática según el sitio):

```bash
python3 scripts/get_transcript.py "<url>" --out /tmp/watch_transcript.txt --timestamps --lang <código>
```

El script imprime JSON con `transcript_file`, `title`, `uploader`, `duration` y `source`. Orden de estrategias: YouTube → `youtube-transcript-api`; cualquier sitio → subtítulos vía `yt-dlp`; si no hay subtítulos → reintentar con `--audio` para descargar el audio y transcribirlo con la herramienta STT disponible.

**Si el entorno no tiene salida directa a internet** (timeout, conexión bloqueada), cambiar al plan B con navegador:
- YouTube: abrir el video con las herramientas de navegador, hacer clic en "…" → "Mostrar transcripción" y copiar el panel (lleva marcas de tiempo).
- Alternativa YouTube sin navegador: probar `https://www.youtube.com/watch?v=<ID>` con herramientas de apertura web de solo lectura, o servicios de transcripción públicos.
- Otros sitios: buscar en el HTML del reproductor el track de subtítulos (`.vtt`/`.srt`) o una API JSON de captions.

Si el video no tiene subtítulos y no es posible transcribir audio, analizar el contenido disponible (título, descripción, capítulos, comentarios) e **indicar claramente al usuario** que el análisis se basa en metadatos, no en el contenido audiovisual.

### 2. Analizar el contenido

Leer la transcripción completa (o en bloques si es muy larga) y producir el análisis con esta estructura, siempre en el idioma del usuario:

1. **Resumen ejecutivo** — de qué trata el video en 2-4 oraciones.
2. **Puntos principales** — los 5-10 argumentos/ideas clave, ordenados por relevancia, cada uno con su marca de tiempo `[HH:MM:SS]`.
3. **Métodos y herramientas** — tabla con: método/paso descrito, herramientas o software mencionados, y para qué sirve.
4. **Elementos accionables para automatización** — lo más valioso para el usuario: procesos repetibles que se puedan convertir en scripts, flujos de trabajo, prompts o integraciones. Para cada uno indicar cómo se podría automatizar (p. ej. "este paso de exportación puede ser un script con la API X").
5. **Pasos concretos** — secuencia numerada para replicar lo que muestra el video.
6. **Enlaces y referencias** — URLs, canales o recursos mencionados en el video.

### 3. Entregar el resultado

- Por defecto: mostrar el análisis en el chat (texto estructurado; sin formato Markdown pesado a menos que `--md`).
- `--md`: mismo análisis con formato Markdown completo.
- `--file`: guardar además en `/mnt/agents/output/` con nombre legible, p. ej. `analisis_<tema>.md` o `transcripcion_<tema>.txt`, y referenciar el archivo al final.

## Notas

- Videos muy largos (>1 h): resumir por secciones/capítulos si el video los tiene; mantener el análisis global por debajo de ~2 páginas y ofrecer detalle por partes.
- Playlists: analizar video por video; respetar `--lang` en cada uno.
- No inventar contenido: todo punto del análisis debe poder rastrearse a un segmento de la transcripción.
