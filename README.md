# CHAR9000

A personal AI friend, life co-pilot, build partner and AI tutor that runs **entirely on your own
Windows 11 PC**. It is built on the same platform as CAL9000 (local LLMs, knowledge base, agents,
automations, image generation), with a personality made for one person and tuned for an
**NVIDIA RTX 4090 (24 GB)** and **128 GB RAM**.

Your chats and documents stay on this PC. Nothing is sent to an online AI service.

## Install (about an hour, mostly model downloads; full steps in `docs/CHAR9000-Installation.md`)

1. Update Windows 11 and install the latest NVIDIA driver (NVIDIA App).
2. Download this repo (Code → Download ZIP, or `git clone`) to e.g. `C:\CHAR9000`.
3. Open **PowerShell as Administrator** in that folder and run:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\install.ps1 -OwnerName "<her name>"
```

If it says WSL was installed, reboot and run the same command again.
When it finishes, open the **CHAR9000** shortcut on the desktop (http://localhost:3000), create your
account (the first one becomes admin), then turn off new sign-ups in Admin Panel → Settings.

## Everyday commands (PowerShell in the CHAR9000 folder)

| Do this | Command |
|---|---|
| Start / stop | `.\scripts\char9000.ps1 start` / `stop` |
| Is everything OK? | `.\scripts\char9000.ps1 status` |
| Add documents to its memory | copy files into `data\files`, then `.\scripts\char9000.ps1 ingest` |
| Free the GPU (before gaming or image work) | `.\scripts\char9000.ps1 free-gpu` |
| Back up | `.\scripts\char9000.ps1 backup` |
| Update | `.\scripts\char9000.ps1 update` |

## Docs

| File | What |
|---|---|
| `docs/CHAR9000-Installation.md` | Full installation instructions, first-time setup, ComfyUI, backup/restore, uninstall, troubleshooting |
| `docs/CHAR9000-Guide.md` | User guide: modes, things to try, knowledge base, crew, automations, AI mini-labs, customizing, privacy |
| `docs/CHAR9000-Architecture.md` | How it works inside (great for learning AI) |
| `identity/personality.md` | Who CHAR9000 is — edit this to shape its personality |
| `identity/core_prompt.md` | The system prompt the model actually receives |
| `identity/charter.md` | Rules and agency levels |

No secrets are stored in this repository; `install.ps1` generates them into `.env` on your PC.
