@echo off
:: ─────────────────────────────────────────────────────────────────────────────
::  Tax Season Invaders – Community Tax
::  WASM build script  (Windows)
:: ─────────────────────────────────────────────────────────────────────────────

echo.
echo  [1/3] Installing / upgrading Pygbag...
.venv\Scripts\python.exe -m pip install --upgrade pygbag

echo.
echo  [2/3] Building WASM bundle...
::  Pygbag expects the entry-point file to be named  main.py  at the project root.
copy /Y game_web.py main.py

.venv\Scripts\python.exe -m pygbag --build --width 900 --height 700 --title "Tax Season Invaders" .

echo.
echo  [3/3] Cleaning up temporary main.py...
del main.py

echo.
echo  Done!  The web bundle is in:  build\web\
echo  Upload that folder to any static web host (GitHub Pages, Netlify, etc.)
echo.
pause
