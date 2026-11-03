# CHAR9000 Installation Instructions (Windows 11)

Full step-by-step setup for CHAR9000 on a Windows 11 PC with an NVIDIA RTX 4090 and 128 GB RAM.
Plan on about an hour; most of it is downloading models (~80 GB).

---

## 1. Requirements

| Item | Minimum | Notes |
|---|---|---|
| OS | Windows 11 22H2 or newer, 64-bit | Home or Pro both work |
| GPU | NVIDIA RTX 4090 (24 GB) | the installer refuses GPUs under ~22 GB |
| RAM | 128 GB | 64 GB works without the optional big model |
| Disk | 250 GB free on an SSD | models ~80 GB (+65 GB for the big model), Docker images ~15 GB, plus your data |
| BIOS | Virtualization enabled (Intel VT-x / AMD SVM) | needed for WSL2/Docker. Check: Task Manager → Performance → CPU → "Virtualization: Enabled" |
| Account | A Windows account with Administrator rights | only for installing |
| Internet | Needed for install and updates | CHAR9000 itself runs offline afterwards |

---

## 2. Before you start

1. **Windows Update:** Settings → Windows Update → install everything, reboot.
2. **NVIDIA driver:** install the **NVIDIA App** from nvidia.com and update to the latest Game Ready or Studio driver. Reboot.
   Check: open PowerShell and run `nvidia-smi`. You should see "NVIDIA GeForce RTX 4090" and about 24564 MiB.
3. **winget:** open PowerShell and run `winget --version`. If it's missing, install "App Installer" from the Microsoft Store.

---

## 3. Get CHAR9000

**Option A: ZIP (simplest).** On GitHub open the CHAR9000 repo → **Code → Download ZIP**, then unzip so the
files are in `C:\CHAR9000` (you should see `C:\CHAR9000\docker-compose.yml`).

**Option B: git.**
```powershell
winget install --id Git.Git -e
git clone https://github.com/<owner>/CHAR9000.git C:\CHAR9000
```
Option B makes updates easier (`char9000.ps1 update` runs `git pull`).

---

## 4. Run the installer

1. Start menu → type **PowerShell** → right-click **Run as administrator**.
2. Run:

```powershell
cd C:\CHAR9000
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\install.ps1 -OwnerName "<her name>"
```

Optional switches:

| Switch | Effect |
|---|---|
| `-AssistantName "Nova"` | gives the assistant a different name in its personality (the model is still `CHAR9000:latest`) |
| `-WithBigModel` | also downloads gpt-oss:120b (65 GB; uses RAM, slower, smarter) |
| `-SkipModels` | skip model downloads (re-runs, or if you pulled them already) |

**What the installer does, in order:**

1. Checks the GPU and RAM.
2. Installs Git, Docker Desktop, Ollama and Python 3.12 with winget if they're missing.
3. Turns on WSL2 if needed. **If it says "WSL installed - reboot", reboot and run the same command again.**
4. Caps Docker/WSL2 memory at 40 GB (`%USERPROFILE%\.wslconfig`) so Windows and games keep plenty.
5. Tunes Ollama for 24 GB (2 models max, 5-minute idle unload, flash attention, 8-bit KV cache, 16k context).
6. Generates random passwords and keys into `C:\CHAR9000\.env`, readable only by your account.
7. Downloads the models (qwen3.6:27b, gpt-oss:20b, qwen2.5-coder:14b, llama3.2-vision, deepseek-r1:8b, gemma3, nomic-embed-text).
8. Puts her name into the personality files and builds the `CHAR9000:latest` model.
9. Starts Docker Desktop and the CHAR9000 containers (first build takes 5–10 minutes).
10. Makes sure the containers can reach Ollama. If not, Ollama is opened to the local machine and a firewall rule blocks it from the network.
11. Adds a **CHAR9000** shortcut to the desktop and runs the health check.

The installer is safe to run again; it keeps an existing `.env` and skips anything already installed.

### First time Docker Desktop starts
Docker Desktop may show a welcome screen and ask you to accept its terms. Accept, skip sign-in
(an account isn't needed), and leave "Use WSL 2 based engine" on (Settings → General). Then re-run
the installer if it timed out waiting for Docker.

---

## 5. First-time setup

1. Double-click **CHAR9000** on the desktop (or open http://localhost:3000).
2. Click **Sign up** and create her account. **The first account becomes the admin.**
3. Turn off further sign-ups: profile icon → **Admin Panel → Settings → General → Enable New Sign Ups: off** → Save.
4. Make CHAR9000 the default: Admin Panel → Settings → Models → `CHAR9000:latest` → set as default (it usually already is).
5. Optional, so the personality knows her name and the date in every chat:
   **Admin Panel → Settings → Models → CHAR9000:latest → System Prompt** → paste the contents of
   `identity\core_prompt.md` (including the Context section; Open WebUI fills in `{{USER_NAME}}` and the date).
6. Open http://localhost:5678 and create the **n8n** owner account (used for automations).
7. Say hi: pick **CHAR9000:latest** and type *"Hi! Friend mode. Tell me about yourself."*

---

## 6. Check it's working

```powershell
cd C:\CHAR9000
.\scripts\health-check.ps1
```

Expected: every line `OK` (ComfyUI shows `--` until you install it) and
`RESULT: All services healthy`. A log is kept in `data\health.log`.

---

## 7. Optional: images and video (ComfyUI)

1. Download **ComfyUI Windows portable (NVIDIA)** from the official ComfyUI GitHub releases page. Unzip to `C:\ComfyUI`.
2. Download the model **flux1-schnell-fp8.safetensors** and put it in
   `C:\ComfyUI\ComfyUI\models\checkpoints\FLUX\`. Only ever use `.safetensors` files; `.ckpt` files can contain code.
3. Edit `C:\ComfyUI\run_nvidia_gpu.bat` and add `--listen 127.0.0.1 --port 8188 --reserve-vram 2` to the end of the `python` line.
4. Double-click `run_nvidia_gpu.bat`; wait until it prints `To see the GUI go to: http://127.0.0.1:8188`.
5. Connect the chat's **Image** button to ComfyUI:
   ```powershell
   cd C:\CHAR9000
   $env:OWUI_EMAIL = "<her login email>"; $env:OWUI_PASSWORD = "<her password>"
   python scripts\owui_enable_comfyui.py
   Remove-Item env:OWUI_PASSWORD
   ```
6. Optional video models (LTX-Video 2B, Wan2.1 T2V 1.3B) can be added later; test workflows with
   `python scripts\comfyui_workflows.py test flux`.

To have ComfyUI start at login: press Win+R → `shell:startup` → put a shortcut to `run_nvidia_gpu.bat` there.

---

## 8. Starting automatically

- **Docker Desktop:** Settings → General → "Start Docker Desktop when you sign in" (on). The containers restart on their own.
- **Ollama:** the installer leaves it in the Windows startup apps; check Settings → Apps → Startup → Ollama is on.
- After a reboot, give it a minute, then open the CHAR9000 shortcut.

---

## 9. Updating

```powershell
cd C:\CHAR9000
.\scripts\char9000.ps1 backup     # always back up first
.\scripts\char9000.ps1 update     # git pull, rebuild, restart, health check
```
Update models any time with `ollama pull <model>`. After updating `qwen3.6:27b` or editing the
personality, re-run `.\scripts\install.ps1 -OwnerName "<her name>" -SkipModels` to rebuild `CHAR9000:latest`.

---

## 10. Backup and restore

Backup (run weekly, or before updates):
```powershell
.\scripts\char9000.ps1 backup
```
This creates `data\backups\<date>\` with the database dump, chat history, n8n and knowledge-base
volumes, and a copy of `.env`. The folder contains secrets, so copy it to a private place (external drive).

Restore to a fresh install: install as normal, then stop the stack (`char9000.ps1 stop`), copy
`env.backup` back to `.env`, and restore each volume:
```powershell
$d = "C:\path\to\backups\2026-11-03"
foreach ($v in "char9000_openwebui","char9000_qdrant","char9000_n8n_storage") {
  docker run --rm -v "${v}:/v" -v "${d}:/b:ro" alpine sh -c "cd /v && tar xzf /b/$v.tgz"
}
docker compose up -d postgres; Start-Sleep 15
Get-Content "$d\postgres.sql" | docker exec -i char9000-postgres psql -U char9000 -d postgres
.\scripts\char9000.ps1 start
```

---

## 11. Uninstall

```powershell
cd C:\CHAR9000
docker compose down -v          # deletes ALL CHAR9000 data (chats, memory, automations)
ollama rm CHAR9000:latest       # repeat for other models to free disk
```
Then delete `C:\CHAR9000` and, if no longer wanted, uninstall Docker Desktop and Ollama from Settings → Apps.

---

## 12. Installation troubleshooting

| Problem | Fix |
|---|---|
| "Run this from an Administrator PowerShell." | Right-click PowerShell → Run as administrator |
| "running scripts is disabled on this system" | Run `Set-ExecutionPolicy -Scope Process Bypass` in the same window first |
| "nvidia-smi not found" | Install/update the NVIDIA driver via the NVIDIA App, reboot |
| WSL/Docker says virtualization is disabled | Enable Intel VT-x / AMD SVM in the BIOS |
| Docker Desktop stuck on "Starting" | Reboot; then `wsl --update` in an admin PowerShell |
| `ollama pull` very slow or fails | Re-run with the same command; downloads resume |
| Health check: Ollama FAIL | Start menu → Ollama; then `.\scripts\char9000.ps1 status` |
| Chat shows no models | Admin Panel → Settings → Connections → Ollama URL must be `http://host.docker.internal:11434` |
| Port 3000 or 5678 already in use | Another app uses it; close it, or change the left-hand port in `docker-compose.yml` |
| Out-of-memory in Docker builds | Close big apps; the 40 GB WSL cap is in `%USERPROFILE%\.wslconfig` |
| Anything else | Run `.\scripts\char9000.ps1 logs <service>` (e.g. `open-webui`, `n8n`, `crewai`) and look at the last errors |
