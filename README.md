# watch — Skill de agente Kimi para analizar videos

Skill que le permite al agente **"ver" videos de YouTube o de cualquier sitio de internet**: extrae la transcripción y genera un análisis estructurado con los puntos principales, los métodos/herramientas mostrados y los elementos accionables para automatizar tu trabajo.

## Uso

```
watch <url-del-video> [--transcript] [--md] [--file] [--lang <código>]
```

| Parámetro | Descripción |
|---|---|
| `--transcript` | Extrae la transcripción completa con marcas de tiempo `[HH:MM:SS]` como archivo `.txt` (o `.md` combinado con `--md`). No hace análisis salvo que se pida. |
| `--md` | Entrega el análisis formateado en Markdown (encabezados, listas, tabla de herramientas). |
| `--file` | Además de mostrar el resultado en el chat, lo guarda como archivo descargable. |
| `--lang <código>` | Idioma preferido de subtítulos (p. ej. `es`, `en`); si no existe, usa el disponible. |

Ejemplo:

```
watch https://www.youtube.com/watch?v=ym84m1kRBQ4 --file
```

## Estructura del análisis

1. **Resumen ejecutivo** — de qué trata el video en 2-4 oraciones.
2. **Puntos principales** — 5-10 ideas clave con marca de tiempo `[HH:MM:SS]`.
3. **Métodos y herramientas** — tabla: paso descrito, herramientas mencionadas, para qué sirve.
4. **Elementos accionables para automatización** — procesos repetibles convertibles en scripts, flujos, prompts o integraciones.
5. **Pasos concretos** — secuencia numerada para replicar lo que muestra el video.
6. **Enlaces y referencias** — URLs, canales y recursos mencionados.

## Instalación en Kimi Work / Kimi Agent

1. Empaqueta la carpeta `watch/` como `.skill` (un zip con la carpeta `watch/` en la raíz) o usa un `watch.skill` ya empaquetado.
2. En Kimi Work (modo Work del cliente de escritorio): panel **Skills** → subir skill local.
3. Invócala escribiendo `/` en el input y eligiendo `watch`, o describiendo la tarea directamente.

## Estructura del repositorio

```
watch/
├── SKILL.md                  # Definición de la skill (frontmatter + flujo de trabajo)
└── scripts/
    └── get_transcript.py     # Extracción de transcripción
                              # (youtube-transcript-api → yt-dlp → audio)
```

## Requisitos del entorno

- Python 3.10+
- Dependencias Python: `yt-dlp`, `youtube-transcript-api` (el agente las instala con pip si faltan)

## Notas

- Probada en **Kimi Work** (agente local con red abierta): la transcripción se obtiene en segundos.
- En entornos con red restringida la skill incluye un plan B vía navegador (panel de transcripción de YouTube / track `.vtt`/`.srt` en el reproductor).
- La skill no inventa contenido: cada punto del análisis se rastrea a un segmento de la transcripción.

## Licencia

[MIT](LICENSE) © 2026 William Valencia
