# Wiki del evento · NTT DATA x UPV Agentic Engineering Hackathon

Sitio estático para participantes (agenda, normas, funcionamiento, requisitos de la app, evaluación y plantillas de agentes). Misma identidad visual que los decks (`02_Presentaciones/html/`): NTT DATA Visual Identity Guidelines v5.2.2, Noto Sans / Noto Serif, Innovation Curve y lockup NTT DATA | UPV.

Sin dependencias: solo Python 3 (biblioteca estándar) para construir.

## Publicar (una sola vez)

El repo es `Salvador-Manzanera-NTT/NTTDATAxUPV-Agentic-Hackthon` y lo crea `06_Skill_Publicar_Epicas/crear-repos-github.sh` (sube esta carpeta, que **es** la raíz del repo, activa Pages con origen **GitHub Actions** y lanza el workflow). A mano sería: crear el repo, subir esta carpeta a `main`, **Settings → Pages → Source: GitHub Actions** y hacer un push a `main`. El workflow `Publicar wiki en GitHub Pages` construye y publica; la URL aparece en el job `deploy` y en Settings → Pages (`https://<org>.github.io/<repo>/`).

A partir de ahí, **cada push a `main` republica la wiki**. Los pull requests solo validan que compila y que no hay enlaces rotos.

> GitHub Pages es público salvo en planes Enterprise con Pages privado. No incluyas claves, listas de alumnos ni datos personales.

## Épicas (sección «Épicas»)

Las épicas **no se editan aquí**: viven en `../05_Epicas/epics/` (privado de la organización) y se publican fase a fase con la skill `06_Skill_Publicar_Epicas` (`/publicar-epicas base|cr1|cr2`), que copia los ficheros a `epicas/<ID>.md` y hace push.

- `build.py` lee `epicas/*.md` y genera `epica-<id>.html` (para leer), `epicas/<ID>.md` (markdown crudo para agentes) y `epicas/index.json`.
- **Hasta que una fase se copia a `epicas/`, no existe ni en el repo ni en el sitio.** Así CR1 y CR2 no se ven antes de su hora.
- Los equipos las descargan con `WebFetch` (el dominio de Pages está permitido en el `settings.json` del template; ver `.claude/hints/epicas.md`).
- No edites a mano `epicas/` salvo para retirar una épica publicada por error.

## Editar contenido

```
src/pages/NN_nombre.html   ← una página por fichero (el orden lo marca NN_)
epicas/                    ← épicas ya publicadas (las copia la skill; vacío hasta el día 1)
src/template.html          ← cabecera, menú lateral, buscador
src/assets/wiki.css        ← estilos (tokens de marca en :root)
src/assets/wiki.js         ← menú móvil, buscador, pestañas, copiar
build.py                   ← genera dist/ (no se versiona; lo construye el workflow)
```

Cada página empieza con metadatos en comentarios (`title`, `kicker`, `lead`, `chips`, `h1`, `home`). Los `<h2>` generan solos su ancla y el índice lateral. Para bloques de código y prompts copiables:

```html
<codeblock file=".claude/agents/ejemplo.md"> …texto tal cual, sin escapar… </codeblock>
<promptblock title="Título"> …texto tal cual… </promptblock>
```

Iconos disponibles: `<svg class="icon"><use href="#i-agent"/></svg>` (mismo sprite que los decks: `i-agent`, `i-check`, `i-clock`, `i-trophy`…).

## Vista previa local

```bash
python3 build.py --check        # construye y comprueba enlaces/anclas
python3 -m http.server -d dist 8000
# abre http://localhost:8000
```

## Pendiente de cerrar (marcado en la wiki con «por confirmar»)

- **La aplicación** (`src/pages/05_app.html`): resumen de BiciCampus publicado el 12-nov-2026 (nombre, historia y roles; sin reglas detalladas ni cambios de requisitos). Si se prefiere no revelarla hasta el día 1, restaurar el bloque «Estado: pendiente».
- Aula, fecha de la sesión de setup (26-nov propuesta), composición del jurado y premios.
- Logos: se usan `ntt-*` y `upv*` de los decks. `upv-inverso.svg` es un derivado pendiente de aprobación de la UPV y el acento UPV es provisional. **No se incluye el logo de Claude**: requiere la aprobación de Lana (Lauk & Key) antes de distribuirlo; de momento solo aparece el texto «Con el apoyo de Claude».
- Contraste con los materiales: mantener la coherencia de horarios con `00_Plan_Hackathon_UPV.md` (CR1 17:45 y CR2 18:15 el día 2; congelación el día 3 a las 17:30).
