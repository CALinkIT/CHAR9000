<#
.SYNOPSIS  CHAR9000 health check for Windows: HTTP endpoints, containers, n8n workers, CHAR9000 model, GPU.
.EXAMPLE   .\scripts\health-check.ps1          # prints OK/FAIL per service, exit code 1 if anything failed
#>
$ErrorActionPreference = "Continue"
$Root = Split-Path -Parent $PSScriptRoot
$log = Join-Path $Root "data\health.log"

$http = [ordered]@{
  "Open WebUI"  = "http://127.0.0.1:3000"
  "n8n"         = "http://127.0.0.1:5678/healthz"
  "CrewAI"      = "http://127.0.0.1:8000/health"
  "Pydantic AI" = "http://127.0.0.1:8001/health"
  "Qdrant"      = "http://127.0.0.1:6333/readyz"
  "Ollama"      = "http://127.0.0.1:11434/api/tags"
}
$optional = [ordered]@{ "ComfyUI" = "http://127.0.0.1:8188" }
$containers = "char9000-postgres", "char9000-redis"

$fail = 0; $lines = @("=== CHAR9000 health $(Get-Date -Format s) ===")
function Probe($url) {
  try { (Invoke-WebRequest $url -UseBasicParsing -TimeoutSec 10).StatusCode } catch {
    if ($_.Exception.Response) { [int]$_.Exception.Response.StatusCode } else { 0 } }
}
foreach ($n in $http.Keys) {
  $c = Probe $http[$n]
  if ($c -eq 200) { $lines += "  OK    $n" } else { $lines += "  FAIL  $n ($c)"; $fail++ }
}
foreach ($n in $optional.Keys) {
  $c = Probe $optional[$n]
  $lines += $(if ($c -eq 200) { "  OK    $n" } else { "  --    $n not running (optional)" })
}
foreach ($ct in $containers) {
  $s = docker inspect -f "{{.State.Status}}/{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}" $ct 2>$null
  if ($s -match '^running/(healthy|none)$') { $lines += "  OK    $ct" } else { $lines += "  FAIL  $ct ($s)"; $fail++ }
}
$w = (docker ps --filter "name=char9000-n8n-worker" --format "{{.Names}}" 2>$null | Measure-Object).Count
if ($w -ge 2) { $lines += "  OK    n8n workers ($w)" } else { $lines += "  FAIL  n8n workers ($w/2)"; $fail++ }
$m = (ollama list 2>$null | Select-String '^CHAR9000:latest')
if ($m) { $lines += "  OK    CHAR9000 model" } else { $lines += "  FAIL  CHAR9000 model missing (re-run install.ps1)"; $fail++ }
$gpu = nvidia-smi --query-gpu=memory.used,memory.total --format=csv,noheader 2>$null
$lines += "  GPU   $gpu"
$lines += $(if ($fail) { "RESULT: $fail problem(s)" } else { "RESULT: All services healthy" })

$lines | ForEach-Object { Write-Host $_ }
New-Item -ItemType Directory -Force (Split-Path $log) | Out-Null
$lines | Add-Content $log
exit [int]($fail -gt 0)
