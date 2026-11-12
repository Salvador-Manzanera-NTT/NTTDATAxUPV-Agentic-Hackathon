#!/usr/bin/env python3
"""Construye la wiki: src/pages/*.html + src/template.html -> dist/*.html

Uso:  python3 build.py            # genera dist/
      python3 build.py --check    # además comprueba enlaces internos y anclas

Cada página es un fragmento HTML con metadatos en comentarios al inicio:
  <!-- title: Agenda -->   <!-- kicker: ... -->   <!-- lead: ... -->
  <!-- icon: i-clock -->   <!-- chips: <span class="chip">..</span> -->  <!-- home: 1 -->
Los <h2> reciben id automático y forman el índice lateral y el buscador.

Épicas: lee epicas/*.md (SOLO lo ya liberado; la skill publicar-epicas copia ahí cada fase) y genera
epica-<id>.html, epicas/<ID>.md (markdown crudo para agentes) y epicas/index.json.
Bloques especiales: <codeblock file="x.md">texto</codeblock> y <promptblock title="..">texto</promptblock>
(se escapan solos, el texto se escribe tal cual).
"""
import datetime, html, json, pathlib, re, shutil, sys, unicodedata

ROOT = pathlib.Path(__file__).parent
SRC, DIST = ROOT / "src", ROOT / "dist"
EPICAS = ROOT / "epicas"
FASES = [("base", "Base · día 1", "Día 1, 16:00"), ("cr1", "Cambio 1", "Día 2, 17:45"), ("cr2", "Cambio 2", "Día 2, 18:15")]


def slug(s):
    s = re.sub(r"<[^>]+>", "", s)
    s = unicodedata.normalize("NFD", html.unescape(s)).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-") or "seccion"


def meta(text):
    m = {}
    for k, v in re.findall(r"<!--\s*(\w+):\s*(.*?)\s*-->", text.split("\n\n", 1)[0] + "\n", re.S):
        m[k] = v
    return m


def strip_meta(text):
    return re.sub(r"\A(\s*<!--\s*\w+:.*?-->\s*)+", "", text, flags=re.S)


def blocks(text):
    def code(m):
        fn = m.group(1) or ""
        body = html.escape(m.group(2).strip("\n"))
        bar = f'<span class="fn">{html.escape(fn)}</span>' if fn else '<span class="fn"></span>'
        return (f'<div class="code"><div class="bar"><i></i><i></i><i></i>{bar}'
                f'<button class="copy" type="button">Copiar</button></div><pre><code>{body}</code></pre></div>')

    def prompt(m):
        t = html.escape(m.group(1) or "Prompt")
        body = html.escape(m.group(2).strip("\n"))
        return (f'<div class="prompt"><div class="hd"><span>{t}</span>'
                f'<button class="copy" type="button">Copiar</button></div><pre>{body}</pre></div>')

    text = re.sub(r'<codeblock(?:\s+file="([^"]*)")?>(.*?)</codeblock>', code, text, flags=re.S)
    text = re.sub(r'<promptblock(?:\s+title="([^"]*)")?>(.*?)</promptblock>', prompt, text, flags=re.S)
    return text


def add_ids(text):
    seen, toc = set(), []

    def h2(m):
        attrs, inner = m.group(1), m.group(2)
        mid = re.search(r'id="([^"]+)"', attrs)
        i = mid.group(1) if mid else slug(inner)
        base, n = i, 2
        while i in seen:
            i, n = f"{base}-{n}", n + 1
        seen.add(i)
        toc.append((i, re.sub(r"<[^>]+>", "", inner).strip()))
        if mid:
            return m.group(0)
        return f'<h2 id="{i}"{attrs}>{inner}</h2>'

    return re.sub(r"<h2([^>]*)>(.*?)</h2>", h2, text, flags=re.S), toc


def plain(s):
    s = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", s, flags=re.S)
    s = re.sub(r"<[^>]+>", " ", s)
    return re.sub(r"\s+", " ", html.unescape(s)).strip()


def frontmatter(text):
    m = re.match(r"\A---\n(.*?)\n---\n?(.*)\Z", text, re.S)
    if not m:
        raise ValueError("falta el frontmatter")
    meta_, body = {}, m.group(2)
    for line in m.group(1).splitlines():
        if ":" not in line or line.lstrip().startswith("#"):
            continue
        k, v = line.split(":", 1)
        v = re.sub(r"\s+#.*$", "", v.strip())
        if v.startswith("[") and v.endswith("]"):
            v = [x.strip().strip("\"'") for x in v[1:-1].split(",") if x.strip()]
        else:
            v = v.strip("\"'")
        meta_[k.strip()] = v
    return meta_, body


def inline(s):
    codes = []

    def keep(m):
        codes.append(m.group(1))
        return f"\x00{len(codes) - 1}\x00"

    s = re.sub(r"`([^`]+)`", keep, s)
    s = html.escape(s, quote=False)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"(?<![\*\w])\*(?!\s)([^*]+?)(?<!\s)\*(?![\*\w])", r"<em>\1</em>", s)
    return re.sub(r"\x00(\d+)\x00", lambda m: f"<code>{html.escape(codes[int(m.group(1))], quote=False)}</code>", s)


def split_row(line):
    cells = re.split(r"(?<!\\)\|", line.strip().strip("|"))
    return [c.strip().replace("\\|", "|") for c in cells]


LISTA = re.compile(r"\s*(?:[-*]|\d+\.)\s+")


def md_to_html(md):
    """Markdown mínimo (el que usan las épicas). Omite el primer H1: lo pinta la cabecera de la página."""
    lines, out, i = md.splitlines(), [], 0
    skipped_h1 = False
    while i < len(lines):
        ln = lines[i]
        if not ln.strip():
            i += 1
        elif ln.startswith("```"):
            i += 1
            buf = []
            while i < len(lines) and not lines[i].startswith("```"):
                buf.append(lines[i])
                i += 1
            i += 1
            out.append('<div class="code"><div class="bar"><i></i><i></i><i></i><span class="fn"></span>'
                       '<button class="copy" type="button">Copiar</button></div>'
                       f'<pre><code>{html.escape(chr(10).join(buf))}</code></pre></div>')
        elif re.match(r"#{1,3} ", ln):
            lvl = len(ln) - len(ln.lstrip("#"))
            txt = ln[lvl:].strip()
            if lvl == 1 and not skipped_h1:
                skipped_h1 = True
            else:
                out.append(f"<h{lvl}>{inline(txt)}</h{lvl}>")
            i += 1
        elif ln.strip() == "---":
            out.append("<hr>")
            i += 1
        elif ln.startswith(">"):
            buf = []
            while i < len(lines) and lines[i].startswith(">"):
                buf.append(lines[i][1:].strip())
                i += 1
            out.append("<blockquote><p>" + inline(" ".join(x for x in buf if x)) + "</p></blockquote>")
        elif ln.lstrip().startswith("|"):
            rows = []
            while i < len(lines) and lines[i].lstrip().startswith("|"):
                rows.append(split_row(lines[i]))
                i += 1
            sep = len(rows) > 1 and re.match(r"^[\s:\-|]+$", "|".join(rows[1]))
            head, body = rows[0], (rows[2:] if sep else rows[1:])
            th = "".join(f"<th>{inline(c)}</th>" for c in head)
            tb = "".join("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>" for r in body)
            out.append(f'<div class="tablewrap"><table><thead><tr>{th}</tr></thead><tbody>{tb}</tbody></table></div>')
        elif LISTA.match(ln):
            ordered = bool(re.match(r"\s*\d+\.", ln))
            items = []
            while i < len(lines) and LISTA.match(lines[i]):
                items.append(LISTA.sub("", lines[i], count=1))
                i += 1
            tag = "ol" if ordered else "ul"
            out.append(f"<{tag}>" + "".join(f"<li>{inline(x)}</li>" for x in items) + f"</{tag}>")
        else:
            buf = []
            while i < len(lines) and lines[i].strip() and not re.match(r"```|#{1,3} |>|\s*\||---$", lines[i]) and not LISTA.match(lines[i]):
                buf.append(lines[i].strip())
                i += 1
            if not buf:
                buf.append(lines[i].strip())
                i += 1
            out.append(f"<p>{inline(' '.join(buf))}</p>")
    return "\n".join(out)


def load_epicas():
    eps = []
    if EPICAS.exists():
        for f in sorted(EPICAS.glob("*.md")):
            meta_, body = frontmatter(f.read_text(encoding="utf-8"))
            for req in ("id", "title", "phase"):
                if req not in meta_:
                    raise ValueError(f"{f.name}: falta '{req}' en el frontmatter")
            if meta_["id"] != f.stem:
                raise ValueError(f"{f.name}: el nombre del fichero debe ser {meta_['id']}.md")
            if meta_["phase"] not in [x[0] for x in FASES]:
                raise ValueError(f"{f.name}: fase '{meta_['phase']}' no válida")
            eps.append(dict(meta_, file=f, body=body, out=f"epica-{meta_['id'].lower()}.html", md=f"epicas/{f.name}"))
    order = {x[0]: n for n, x in enumerate(FASES)}
    eps.sort(key=lambda e: (order[e["phase"]], int(re.sub(r"\D", "", e["id"]) or 0)))
    return eps


def epicas_lista(eps):
    released = {e["phase"] for e in eps}
    fases = "".join(
        f'<div class="card {"ok" if k in released else "warn"}"><h3>{html.escape(nom)}</h3>'
        f'<p>{html.escape(cuando)}</p><p><span class="chip {"ok" if k in released else "pend"}">'
        f'{"Publicada" if k in released else "Aún no publicada"}</span></p></div>' for k, nom, cuando in FASES)
    if eps:
        rows = "".join(
            f'<tr><td><strong>{html.escape(e["id"])}</strong></td><td><a href="{e["out"]}">{html.escape(e["title"])}</a></td>'
            f'<td>{html.escape(e["phase"])}</td><td>{html.escape(e.get("priority", "-"))}</td><td>{html.escape(e.get("size", "-"))}</td>'
            f'<td><a href="{e["md"]}">{html.escape(e["id"])}.md</a></td></tr>' for e in eps)
        tabla = ('<div class="tablewrap"><table><thead><tr><th>Id</th><th>Épica</th><th>Fase</th><th>Prioridad</th><th>Tamaño</th>'
                 f'<th>Markdown</th></tr></thead><tbody>{rows}</tbody></table></div>')
    else:
        tabla = ('<div class="pending"><svg class="icon"><use href="#i-clock"/></svg><div><h3>Todavía no hay épicas publicadas</h3>'
                 '<p>Las épicas base aparecen aquí el <strong>día 1, antes de las 16:00</strong>. Recargad la página: '
                 'en cuanto estén publicadas, esta tabla se rellena.</p></div></div>')
    return f'<div class="cards">{fases}</div>\n{tabla}'


def build_nav(pages, cur_n, sub=""):
    nav = []
    for q in pages:
        cur = q["n"] == cur_n
        nav.append(f'      <li class="{"cur" if cur else ""}"><a href="{q["out"]}"'
                   f'{" aria-current=page" if cur else ""}><span class="n">{q["n"] + 1}</span>{html.escape(q["m"].get("title", ""))}</a>'
                   f'{sub if cur else ""}</li>')
    return "\n".join(nav)


def main():
    check = "--check" in sys.argv
    tpl = (SRC / "template.html").read_text(encoding="utf-8")
    sprite = (SRC / "sprite.svg.html").read_text(encoding="utf-8")
    eps = load_epicas()
    files = sorted((SRC / "pages").glob("*.html"))
    pages = []
    for i, f in enumerate(files):
        raw = f.read_text(encoding="utf-8")
        m = meta(raw)
        raw = raw.replace("<!--EPICAS_LISTA-->", epicas_lista(eps))
        body, toc = add_ids(blocks(strip_meta(raw)))
        name = re.sub(r"^\d+_", "", f.stem)
        pages.append(dict(m=m, body=body, toc=toc, out="index.html" if i == 0 else f"{name}.html", n=i))
    epi_page = next((p for p in pages if p["m"].get("epicas")), None)

    built = datetime.date.today().strftime("%d-%m-%Y")
    if DIST.exists():
        shutil.rmtree(DIST)
    (DIST / "assets").mkdir(parents=True)
    shutil.copytree(SRC / "assets" / "fonts", DIST / "assets" / "fonts")
    shutil.copytree(SRC / "assets" / "logos", DIST / "assets" / "logos")
    shutil.copy(SRC / "assets" / "wiki.css", DIST / "assets" / "wiki.css")
    shutil.copy(SRC / "assets" / "wiki.js", DIST / "assets" / "wiki.js")
    (DIST / ".nojekyll").write_text("")

    # épicas: markdown crudo para agentes + índice JSON + páginas HTML
    (DIST / "epicas").mkdir()
    for e in eps:
        shutil.copy(e["file"], DIST / e["md"])
        e["html_body"], e["toc"] = add_ids(md_to_html(e["body"]))
    (DIST / "epicas" / "index.json").write_text(json.dumps(dict(
        actualizado=datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
        fases_publicadas=sorted({e["phase"] for e in eps}),
        epicas=[dict(id=e["id"], titulo=e["title"], fase=e["phase"], prioridad=e.get("priority"), tamano=e.get("size"),
                     etiquetas=e.get("labels", []), md=e["md"], html=e["out"]) for e in eps]),
        ensure_ascii=False, indent=2), encoding="utf-8")

    # índice de búsqueda
    idx = []
    for p in pages:
        t = p["m"].get("title", p["out"])
        parts = re.split(r"(?=<h2 )", p["body"])
        idx.append(dict(t=t, p="Página", u=p["out"], x=plain(p["m"].get("lead", ""))))
        for part in parts:
            h = re.match(r'<h2 id="([^"]+)"[^>]*>(.*?)</h2>', part, re.S)
            if h:
                idx.append(dict(t=plain(h.group(2)), p=t, u=f'{p["out"]}#{h.group(1)}', x=plain(part)[:1800]))
    for e in eps:
        idx.append(dict(t=f'{e["id"]} · {e["title"]}', p="Épicas", u=e["out"], x=plain(e["html_body"])[:1800]))
    (DIST / "assets" / "search-index.js").write_text(
        "window.WIKI_INDEX=" + json.dumps(idx, ensure_ascii=False, separators=(",", ":")) + ";", encoding="utf-8")

    def fill(title, desc, nav, hero, content, pager, home=False):
        full_title = title if home else f"{title} · Agentic Engineering Hackathon"
        return (tpl.replace("{{TITLE}}", html.escape(full_title)).replace("{{DESC}}", html.escape(desc))
                .replace("{{SPRITE}}", sprite).replace("{{NAV}}", nav).replace("{{HERO}}", hero)
                .replace("{{CONTENT}}", content).replace("{{PAGER}}", pager).replace("{{BUILT}}", built))

    def epic_sub(cur_id=None):
        if not eps:
            return ""
        return "<ul>" + "".join(
            f'<li><a href="{e["out"]}"{" aria-current=page" if e["id"] == cur_id else ""}>{html.escape(e["id"])} · {html.escape(e["title"][:34])}</a></li>'
            for e in eps) + "</ul>"

    for p in pages:
        m = p["m"]
        title = m.get("title", "Wiki")
        sub = ""
        if p is epi_page:
            sub = epic_sub()
        elif p["toc"]:
            sub = "<ul>" + "".join(f'<li><a href="#{i}">{html.escape(t)}</a></li>' for i, t in p["toc"]) + "</ul>"
        home = m.get("home")
        chips = f'<div class="chips">{m["chips"]}</div>' if m.get("chips") else ""
        hero = (f'<section class="hero{" home" if home else ""}">'
                f'<svg class="curve" aria-hidden="true"><use href="#curve"/></svg>'
                f'<p class="kicker">{m.get("kicker", "")}</p><h1>{m.get("h1", title)}</h1>'
                f'<p class="lead">{m.get("lead", "")}</p>{chips}</section>')
        prev = pages[p["n"] - 1] if p["n"] > 0 else None
        nxt = pages[p["n"] + 1] if p["n"] + 1 < len(pages) else None
        pager = '<nav class="pager" aria-label="Siguiente y anterior">'
        pager += (f'<a class="prev" href="{prev["out"]}"><small>Anterior</small>← {html.escape(prev["m"]["title"])}</a>' if prev else "<span></span>")
        pager += (f'<a class="next" href="{nxt["out"]}"><small>Siguiente</small>{html.escape(nxt["m"]["title"])} →</a>' if nxt else "")
        pager += "</nav>"
        (DIST / p["out"]).write_text(fill(title, plain(m.get("lead", "")), build_nav(pages, p["n"], sub), hero, p["body"], pager, home), encoding="utf-8")

    for e in eps:
        chips = (f'<span class="chip blue">Fase {html.escape(e["phase"])}</span>'
                 f'<span class="chip line">Prioridad {html.escape(e.get("priority", "-"))}</span>'
                 + (f'<span class="chip line">Tamaño {html.escape(e["size"])}</span>' if e.get("size") else "")
                 + f'<a class="chip line" href="{e["md"]}">Markdown para agentes</a>')
        hero = ('<section class="hero"><svg class="curve" aria-hidden="true"><use href="#curve"/></svg>'
                f'<p class="kicker">Épica {html.escape(e["id"])}</p><h1>{html.escape(e["title"])}</h1>'
                f'<p class="lead">Contrato oficial de requisitos. No se edita: lo que dice esta página es lo que se comprueba.</p>'
                f'<div class="chips">{chips}</div></section>')
        pager = ('<nav class="pager" aria-label="Volver"><a class="prev" href="' + (epi_page["out"] if epi_page else "index.html") +
                 '"><small>Volver</small>← Todas las épicas</a></nav>')
        nav = build_nav(pages, epi_page["n"] if epi_page else -1, epic_sub(e["id"]))
        (DIST / e["out"]).write_text(fill(f'{e["id"]} · {e["title"]}', f'Épica {e["id"]} del hackathon', nav, hero, e["html_body"], pager), encoding="utf-8")

    (DIST / "404.html").write_text(
        tpl.replace("{{TITLE}}", "Página no encontrada").replace("{{DESC}}", "").replace("{{SPRITE}}", sprite)
        .replace("{{NAV}}", "").replace("{{BUILT}}", built).replace("{{PAGER}}", "")
        .replace("{{HERO}}", '<section class="hero"><p class="kicker">404</p><h1>Esta página no existe</h1></section>')
        .replace("{{CONTENT}}", '<p><a href="index.html">Volver al inicio de la wiki</a></p>'), encoding="utf-8")

    fases = ", ".join(sorted({e["phase"] for e in eps})) or "ninguna"
    print(f"OK · {len(pages)} páginas + {len(eps)} épicas (fases publicadas: {fases}) -> {DIST}")
    if check:
        sys.exit(0 if verify() else 1)


def verify():
    ids = {}
    for f in DIST.glob("*.html"):
        ids[f.name] = set(re.findall(r'\sid="([^"]+)"', f.read_text(encoding="utf-8")))
    bad = 0
    for f in DIST.glob("*.html"):
        t = f.read_text(encoding="utf-8")
        for href in re.findall(r'href="([^"]+)"', t):
            if href.startswith(("http", "mailto:", "data:")):
                continue
            pg, _, frag = href.partition("#")
            pg = pg or f.name
            if not (DIST / pg).exists() and not pg.startswith("assets"):
                print(f"  ✗ {f.name}: enlace roto -> {href}")
                bad += 1
            elif frag and pg in ids and frag not in ids[pg]:
                print(f"  ✗ {f.name}: ancla inexistente -> {href}")
                bad += 1
        for src in re.findall(r'(?:src|href)="(assets/[^"]+)"', t):
            if not (DIST / src).exists():
                print(f"  ✗ {f.name}: recurso inexistente -> {src}")
                bad += 1
    print("Enlaces y anclas: " + ("todo correcto ✓" if not bad else f"{bad} problemas"))
    return not bad


if __name__ == "__main__":
    main()
