#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
watcher.py - Web Watcher (ranking SR -> GitHub Pages)
Monitorea sr_index.html (generado por el plugin dentro de SourceMod/data)
y cuando cambia lo copia a la carpeta E:\\L4D2SVR\\kdm\\ (repo de GitHub Pages) y hace git push.
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
# Archivo generado por el plugin (dentro de SourceMod, siempre accesible)
# Ranking que genera el plugin: juego (Steam) y servidor dedicado. Se sube el mas reciente.
SM_INDEX_RUTAS = [
    Path(r"E:\Steam\steamapps\common\Left 4 Dead 2\left4dead2\addons\sourcemod\data\sr_index.html"),
    Path(r"E:\L4D2SVR\left4dead2\addons\sourcemod\data\sr_index.html"),
]


def sm_index():
    existentes = [p for p in SM_INDEX_RUTAS if p.exists()]
    if not existentes:
        return SM_INDEX_RUTAS[0]
    return max(existentes, key=lambda p: p.stat().st_mtime)


# Destino: repo de GitHub Pages
REPO_DIR    = Path(r"E:\L4D2SVR\kdm")
INDEX_HTML  = REPO_DIR / "index.html"
LOG_FILE    = REPO_DIR / "logs" / "web_updater.log"
GIT_MSG     = "auto: actualizar ranking y partidas"
POLL_SECS   = 3

# Servidor web para el MOTD (0 = apagado)
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


def git_push():
    git(["add", "index.html"])
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


def copiar_y_subir(motivo):
    log(f"{motivo}. Copiando a kdm/...")
    shutil.copy2(sm_index(), INDEX_HTML)
    log(f"Copiado OK ({INDEX_HTML.stat().st_size} bytes). Haciendo git push...")
    git_push()


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


def main():
    log(f"Watcher iniciado.")
    iniciar_web()
    for r in SM_INDEX_RUTAS:
        log(f"Monitoreando: {r}")
    log(f"Destino:      {INDEX_HTML}")

    SM_INDEX = sm_index()
    prev_mtime = SM_INDEX.stat().st_mtime if SM_INDEX.exists() else 0.0

    # Al arrancar: si ya hay un ranking generado y no esta en kdm/ (o es distinto), subirlo
    try:
        if SM_INDEX.exists():
            distinto = (not INDEX_HTML.exists()) or (SM_INDEX.read_bytes() != INDEX_HTML.read_bytes())
            if distinto:
                copiar_y_subir("Ranking pendiente al iniciar")
    except Exception as e:
        log(f"Error al iniciar: {e}")

    while True:
        try:
            SM_INDEX = sm_index()
            if SM_INDEX.exists():
                curr_mtime = SM_INDEX.stat().st_mtime
                if curr_mtime > prev_mtime:
                    prev_mtime = curr_mtime
                    copiar_y_subir("sr_index.html actualizado")
        except Exception as e:
            log(f"Error: {e}")

        time.sleep(POLL_SECS)


if __name__ == "__main__":
    main()
