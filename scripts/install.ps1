<#
.SYNOPSIS
  Installs CHAR9000 on Windows 11 (RTX 4090 / 128 GB profile). Safe to re-run.

.EXAMPLE
  # From an *Administrator* PowerShell in the CHAR9000 folder:
  Set-ExecutionPolicy -Scope Process Bypass
  .\scripts\install.ps1 -OwnerName "Emma"
  .\scripts\install.ps1 -OwnerName "Emma" -WithBigModel     # also gpt-oss:120b (65 GB, runs partly in RAM)

.NOTES
  Installs (via winget, if missing): Git, Docker Desktop, Ollama, Python 3.12.
  Does not install NVIDIA drivers (use the GeForce/NVIDIA App) or ComfyUI (see docs\CHAR9000-Guide.md).
#>
[CmdletBinding()]
param(
  [Parameter(Mandatory)] [string] $OwnerName,
  [string] $AssistantName = "CHAR9000",
  [switch] $WithBigModel,
  [switch] $SkipModels
)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
function Step($m) { Write-Host "`n== $m" -ForegroundColor Cyan }
function Have($cmd) { [bool](Get-Command $cmd -ErrorAction SilentlyContinue) }

# --- 0. admin + hardware -------------------------------------------------------
$admin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
  [Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $admin) { throw "Run this from an Administrator PowerShell." }

Step "Checking hardware"
if (-not (Have nvidia-smi)) { throw "nvidia-smi not found - install the latest NVIDIA driver first." }
$gpu  = (& nvidia-smi --query-gpu=name,memory.total --format=csv,noheader,nounits | Select-Object -First 1).Split(",")
$vram = [int]$gpu[1].Trim()
$ramGB = [math]::Round((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory / 1GB)
Write-Host "GPU: $($gpu[0].Trim()) ($vram MiB)  RAM: $ramGB GB"
if ($vram -lt 22000) { throw "This profile needs a 24 GB GPU (RTX 4090)." }
if ($WithBigModel -and $ramGB -lt 100) { Write-Warning "Less than 128 GB RAM - skipping the big model."; $WithBigModel = $false }

# --- 1. prerequisites ------------------------------------------------------------
Step "Installing prerequisites (winget)"
$pkgs = @{ git = "Git.Git"; docker = "Docker.DockerDesktop"; ollama = "Ollama.Ollama"; python = "Python.Python.3.12" }
foreach ($cmd in $pkgs.Keys) {
  if (Have $cmd) { Write-Host "  $cmd present" }
  else {
    winget install --id $pkgs[$cmd] -e --accept-source-agreements --accept-package-agreements --silent
    $env:Path = [Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [Environment]::GetEnvironmentVariable("Path", "User")
  }
}
wsl --status *> $null; if ($LASTEXITCODE -ne 0) { wsl --install --no-distribution; Write-Warning "WSL installed - reboot, then re-run this script."; exit 0 }

# --- 2. WSL2 memory cap (Docker Desktop) ----------------------------------------
Step "Capping WSL2/Docker memory at 40 GB"
$wslcfg = Join-Path $env:USERPROFILE ".wslconfig"
@"
[wsl2]
memory=40GB
processors=12
swap=8GB
"@ | Set-Content -Encoding ascii $wslcfg

# --- 3. Ollama tuning (user env vars, restart Ollama) ---------------------------
Step "Tuning Ollama for 24 GB VRAM"
$ollamaEnv = @{
  OLLAMA_MAX_LOADED_MODELS = "2"; OLLAMA_NUM_PARALLEL = "2"; OLLAMA_KEEP_ALIVE = "5m"
  OLLAMA_FLASH_ATTENTION = "1"; OLLAMA_KV_CACHE_TYPE = "q8_0"; OLLAMA_CONTEXT_LENGTH = "16384"
}
foreach ($k in $ollamaEnv.Keys) { [Environment]::SetEnvironmentVariable($k, $ollamaEnv[$k], "User"); Set-Item "env:$k" $ollamaEnv[$k] }
Get-Process "ollama*" -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Process "$env:LOCALAPPDATA\Programs\Ollama\ollama app.exe" -ErrorAction SilentlyContinue
if (-not (Get-Process "ollama*" -ErrorAction SilentlyContinue)) { Start-Process ollama -ArgumentList serve -WindowStyle Hidden }
for ($i = 0; $i -lt 30; $i++) { try { Invoke-RestMethod http://127.0.0.1:11434/api/tags | Out-Null; break } catch { Start-Sleep 2 } }

# --- 4. .env with generated secrets ---------------------------------------------
Step "Creating .env (secrets generated locally, never committed)"
function NewSecret { -join ((1..32) | ForEach-Object { '{0:x2}' -f (Get-Random -Maximum 256) }) }
if (-not (Test-Path .env)) {
  $tz = try { (& tzutil /g) } catch { "Eastern Standard Time" }
  $ianaTz = @{ "Eastern Standard Time"="America/New_York"; "Central Standard Time"="America/Chicago";
               "Mountain Standard Time"="America/Denver"; "Pacific Standard Time"="America/Los_Angeles" }[$tz]
  if (-not $ianaTz) { $ianaTz = "America/New_York" }
  @"
POSTGRES_USER=char9000
POSTGRES_PASSWORD=$(NewSecret)
POSTGRES_DB=n8n
REDIS_PASSWORD=$(NewSecret)
QDRANT_API_KEY=$(NewSecret)
N8N_ENCRYPTION_KEY=$(NewSecret)
N8N_USER_MANAGEMENT_JWT_SECRET=$(NewSecret)
WEBUI_SECRET_KEY=$(NewSecret)
TZ=$ianaTz
CHAR9000_MODEL_MAIN=qwen3.6:27b
CHAR9000_MODEL_CODER=qwen2.5-coder:14b
CHAR9000_MODEL_LIGHT=gemma3
"@ | Set-Content -Encoding ascii .env
  # only the current user (and SYSTEM/Administrators) can read it
  icacls .env /inheritance:r /grant:r "$($env:USERNAME):(R,W)" "SYSTEM:(F)" "Administrators:(F)" | Out-Null
} else { Write-Host "  .env exists - keeping it" }
New-Item -ItemType Directory -Force data\files, data\shared, data\backups | Out-Null

# --- 5. models -----------------------------------------------------------------
if (-not $SkipModels) {
  Step "Downloading models (~70 GB; this takes a while)"
  $models = "qwen3.6:27b", "gpt-oss:20b", "qwen2.5-coder:14b", "llama3.2-vision", "deepseek-r1:8b", "gemma3", "nomic-embed-text"
  if ($WithBigModel) { $models += "gpt-oss:120b" }
  foreach ($m in $models) { ollama pull $m; if ($LASTEXITCODE -ne 0) { throw "ollama pull $m failed" } }
}

# --- 6. personality: fill in names, build the CHAR9000 model --------------------
Step "Building the $AssistantName personality model"
foreach ($f in "identity\core_prompt.md", "identity\personality.md", "identity\charter.md") {
  (Get-Content -Raw $f).Replace("{{OWNER_NAME}}", $OwnerName) | Set-Content -Encoding utf8 $f
}
$prompt = (Get-Content -Raw identity\core_prompt.md)
$prompt = ($prompt -split "`r?`nContext:")[0].Trim()          # {{...}} context vars are filled by Open WebUI, not Ollama
if ($AssistantName -ne "CHAR9000") { $prompt = $prompt.Replace("CHAR9000", $AssistantName) }
$modelfile = "FROM qwen3.6:27b`nPARAMETER num_ctx 16384`nPARAMETER temperature 0.7`nSYSTEM `"`"`"`n$($prompt.Replace('"""','"'))`n`"`"`"`n"
$mf = Join-Path $env:TEMP "CHAR9000.modelfile"; Set-Content -Encoding utf8 $mf $modelfile
ollama create "CHAR9000:latest" -f $mf
if ($LASTEXITCODE -ne 0) { throw "ollama create failed (is qwen3.6:27b downloaded?)" }

# --- 7. Docker stack -----------------------------------------------------------
Step "Starting Docker Desktop and the CHAR9000 stack"
if (-not (Get-Process "Docker Desktop" -ErrorAction SilentlyContinue)) {
  Start-Process "$env:ProgramFiles\Docker\Docker\Docker Desktop.exe"
}
for ($i = 0; $i -lt 60; $i++) { docker info *> $null; if ($LASTEXITCODE -eq 0) { break }; Start-Sleep 5 }
docker compose up -d --build
if ($LASTEXITCODE -ne 0) { throw "docker compose up failed" }

# Containers must reach Ollama. If they can't, let Ollama listen on all interfaces and
# block port 11434 from the network with Windows Firewall so only this PC can use it.
Step "Checking containers can reach Ollama"
Start-Sleep 10
docker exec char9000-open-webui curl -sf http://host.docker.internal:11434/api/tags *> $null
if ($LASTEXITCODE -ne 0) {
  [Environment]::SetEnvironmentVariable("OLLAMA_HOST", "0.0.0.0:11434", "User")
  if (-not (Get-NetFirewallRule -DisplayName "CHAR9000 block Ollama LAN" -ErrorAction SilentlyContinue)) {
    New-NetFirewallRule -DisplayName "CHAR9000 block Ollama LAN" -Direction Inbound -Protocol TCP -LocalPort 11434 `
      -RemoteAddress Internet, LocalSubnet -Action Block | Out-Null
  }
  Get-Process "ollama*" -ErrorAction SilentlyContinue | Stop-Process -Force
  $env:OLLAMA_HOST = "0.0.0.0:11434"; Start-Process ollama -ArgumentList serve -WindowStyle Hidden; Start-Sleep 5
}

# --- 8. desktop shortcut + health ----------------------------------------------
$lnk = Join-Path ([Environment]::GetFolderPath("Desktop")) "$AssistantName.url"
"[InternetShortcut]`nURL=http://localhost:3000" | Set-Content -Encoding ascii $lnk

Step "Health check"
& "$PSScriptRoot\health-check.ps1"

Write-Host @"

$AssistantName is ready:  http://localhost:3000  (desktop shortcut added)
1. Open it and create $OwnerName's account - the first account becomes the admin.
2. Then: Admin Panel > Settings > General > turn OFF 'Enable New Sign Ups'.
3. Pick the model 'CHAR9000:latest' and say hi.
Guide with things to try: docs\CHAR9000-Guide.md
"@ -ForegroundColor Green
