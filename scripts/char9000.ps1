<#
.SYNOPSIS  Start, stop, restart, update or back up CHAR9000.
.EXAMPLE   .\scripts\char9000.ps1 start | stop | restart | status | logs [service] | update | backup | free-gpu | ingest
#>
param([Parameter(Mandatory)][ValidateSet("start","stop","restart","status","logs","update","backup","free-gpu","ingest")] $Action,
      [string] $Service)
$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)

switch ($Action) {
  "start"    { docker compose up -d; & .\scripts\health-check.ps1 }
  "stop"     { docker compose stop }                              # keeps all data
  "restart"  { if ($Service) { docker compose restart $Service } else { docker compose restart } }
  "status"   { & .\scripts\health-check.ps1; ollama ps }
  "logs"     { if ($Service) { docker compose logs -f --tail 100 $Service } else { docker compose logs --tail 50 } }
  "update"   { git pull; docker compose build; docker compose up -d; & .\scripts\health-check.ps1 }
  "free-gpu" { ollama ps | Select-Object -Skip 1 | ForEach-Object { ($_ -split '\s+')[0] } | Where-Object { $_ } |
                 ForEach-Object { ollama stop $_ }; nvidia-smi --query-gpu=memory.used,memory.total --format=csv }
  "ingest"   { docker compose --profile ingest run --rm ingest --source /data/files --collection my_documents }
  "backup"   {
    $d = "data\backups\$(Get-Date -Format yyyy-MM-dd)"; New-Item -ItemType Directory -Force $d | Out-Null
    $u = (Select-String -Path .env -Pattern '^POSTGRES_USER=(.*)').Matches.Groups[1].Value
    docker exec char9000-postgres pg_dumpall -U $u | Set-Content -Encoding utf8 "$d\postgres.sql"
    foreach ($v in "char9000_openwebui", "char9000_qdrant", "char9000_n8n_storage") {
      docker run --rm -v "${v}:/v:ro" -v "${PWD}\${d}:/b" alpine tar czf "/b/$v.tgz" -C /v .
    }
    Copy-Item .env "$d\env.backup"   # contains secrets - keep the backup folder private
    Get-ChildItem $d | Format-Table Name, Length
  }
}
