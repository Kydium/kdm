#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
watcher.py - Web Watcher (ranking SR -> GitHub Pages)
Monitorea data/sr_web_out/ (paginas que genera el plugin SR con el Top 10)
y cuando cambian las copia a E:\\L4D2SVR\\kdm\\ (repo de GitHub Pages) y hace git push.
Link: https://kydium.github.io/kdm/

Ademas sirve la carpeta kdm/ por HTTP (sin https) en el puerto WEB_PUERTO,
para el MOTD del juego: su navegador no abre paginas https (error -107).
Con un tunel TCP de Playit a ese puerto, todos pueden verla.
"""

import sys
import time
import shutil
import subprocess
import threading
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from datetime import datetime

# ─── CONFIGURACION ────────────────────────────────────────────────────────────
# Paginas que genera el plugin SR en el juego de Steam (host local).
# Cada .html de esa carpeta se copia tal cual a kdm/ y se sube a GitHub.
WEB_OUT     = Path(r"E:\Steam\steamapps\common\Left 4 Dead 2\left4dead2\addons\sourcemod\data\sr_web_out")

# Destino: repo de GitHub Pages
REPO_DIR    = Path(r"E:\L4D2SVR\kdm")
LOG_FILE    = REPO_DIR / "logs" / "web_updater.log"
GIT_MSG     = "auto: actualizar paginas (top 10)"
POLL_SECS   = 3

# Servidor web local (0 = apagado; ya no se usa)
WEB_PUERTO  = 0
# ─────────────────────────────────────────────────────────────────────────────


def log(msg):
    ts   = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def git(args):
    result = subprocess.run(
        ["git"] + args,
        cwd=str(REPO_DIR),
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        if "nothing to commit" in result.stdout + result.stderr:
            return False
        log(f"Git error ({' '.join(args)}): {result.stderr.strip()}")
        return False
    return True


def git_push(nombres):
    for n in nombres:
        git(["add", n])
    ok = git(["commit", "-m", GIT_MSG])
    if not ok:
        log("Sin cambios nuevos.")
        return
    # Traer antes lo que haya en GitHub (por si se cambio algo desde la web)
    git(["pull", "--rebase", "--autostash", "origin", "main"])
    if git(["push", "origin", "main"]):
        log("Push a GitHub Pages completado.")
    else:
        log("No se pudo hacer push (revisa el log de arriba).")


def sincronizar(motivo):
    """Copia a kdm/ las paginas que cambiaron. Devuelve la lista copiada."""
    if not WEB_OUT.exists():
        return []
    copiadas = []
    for src in sorted(WEB_OUT.glob("*.html")):
        dst = REPO_DIR / src.name
        try:
            if dst.exists() and dst.read_bytes() == src.read_bytes():
                continue
            shutil.copy2(src, dst)
            copiadas.append(src.name)
        except Exception as e:
            log(f"No se pudo copiar {src.name}: {e}")
    if copiadas:
        log(f"{motivo}: {', '.join(copiadas)}. Haciendo git push...")
        git_push(copiadas)
    return copiadas


class MotdHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(REPO_DIR), **kwargs)

    def end_headers(self):
        # Que siempre muestre el ranking al dia
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        super().end_headers()

    def guess_type(self, path):
        p = str(path).lower()
        if p.endswith(".woff2"): return "font/woff2"
        if p.endswith(".woff"):  return "font/woff"
        if p.endswith(".html"):  return "text/html; charset=utf-8"
        return super().guess_type(path)

    def log_message(self, fmt, *args):
        pass   # sin spam en la consola


def iniciar_web():
    if not WEB_PUERTO:
        return
    try:
        srv = ThreadingHTTPServer(("0.0.0.0", WEB_PUERTO), MotdHandler)
    except Exception as e:
        log(f"No se pudo abrir el servidor web en el puerto {WEB_PUERTO}: {e}")
        return
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    log(f"Servidor web del MOTD: http://127.0.0.1:{WEB_PUERTO}/comandos.html")


def firma():
    """Fechas de modificacion de las paginas generadas (para notar cambios)."""
    if not WEB_OUT.exists():
        return ()
    return tuple((p.name, p.stat().st_mtime) for p in sorted(WEB_OUT.glob("*.html")))


def main():
    log("Watcher iniciado.")
    iniciar_web()
    log(f"Monitoreando: {WEB_OUT}")
    log(f"Destino:      {REPO_DIR}")

    # Al arrancar: subir lo que este pendiente
    try:
        sincronizar("Pendiente al iniciar")
    except Exception as e:
        log(f"Error al iniciar: {e}")

    prev = firma()
    while True:
        try:
            ahora = firma()
            if ahora != prev:
                prev = ahora
                time.sleep(1)   # que el plugin termine de escribir
                sincronizar("Paginas actualizadas")
        except Exception as e:
            log(f"Error: {e}")
        time.sleep(POLL_SECS)


if __name__ == "__main__":
    main()
