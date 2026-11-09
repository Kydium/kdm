#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
watcher.py - Web Watcher (ranking SR -> GitHub Pages)
Monitorea sr_index.html (generado por el plugin dentro de SourceMod/data)
y cuando cambia lo copia a la carpeta kdm/ (repo de GitHub Pages) y hace git push.
Link: https://kydium.github.io/kdm/
"""

import sys
import time
import shutil
import subprocess
from pathlib import Path
from datetime import datetime

# ─── CONFIGURACION ────────────────────────────────────────────────────────────
# Archivo generado por el plugin (dentro de SourceMod, siempre accesible)
SM_INDEX = Path(r"E:\Steam\steamapps\common\Left 4 Dead 2\left4dead2\addons\sourcemod\data\sr_index.html")

# Destino: repo de GitHub Pages
REPO_DIR    = Path(r"E:\Steam\steamapps\common\Left 4 Dead 2\kdm")
INDEX_HTML  = REPO_DIR / "index.html"
LOG_FILE    = REPO_DIR / "logs" / "web_updater.log"
GIT_MSG     = "auto: actualizar ranking y partidas"
POLL_SECS   = 3
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
    if ok:
        git(["push"])
        log("Push a GitHub Pages completado.")
    else:
        log("Sin cambios nuevos.")


def main():
    log(f"Watcher iniciado.")
    log(f"Monitoreando: {SM_INDEX}")
    log(f"Destino:      {INDEX_HTML}")

    prev_mtime = SM_INDEX.stat().st_mtime if SM_INDEX.exists() else 0.0

    while True:
        try:
            if SM_INDEX.exists():
                curr_mtime = SM_INDEX.stat().st_mtime
                if curr_mtime > prev_mtime:
                    prev_mtime = curr_mtime
                    log("sr_index.html actualizado. Copiando a kdm/...")
                    shutil.copy2(SM_INDEX, INDEX_HTML)
                    log(f"Copiado OK ({INDEX_HTML.stat().st_size} bytes). Haciendo git push...")
                    git_push()
        except Exception as e:
            log(f"Error: {e}")

        time.sleep(POLL_SECS)


if __name__ == "__main__":
    main()
