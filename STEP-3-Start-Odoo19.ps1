<#
.SYNOPSIS
    STEP-3 : Start Odoo 19 + Nginx + Cloudflare DDNS (สคริปต์ start ตัวเดียวของโปรเจกต์)

.DESCRIPTION
    รวมสคริปต์ start ทั้งหมดไว้ที่เดียว (แทน start_odoo.ps1 และ start-odoo19.bat ที่ยกเลิกไปแล้ว)
    ก่อนเริ่มระบบจะเคลียร์ทุก process / service / database session ที่ "ไม่ตรง" รูปแบบ odoo19_p*
    เพราะ Odoo server หรือ connection ที่ค้างอยู่บนฐานข้อมูลอื่นเป็นสาเหตุหลักที่ทำให้เครื่องค้าง

    ขั้นตอน:
      [1/5] เคลียร์ Odoo process ค้าง + process ที่จับพอร์ต Odoo + PostgreSQL service อื่น
      [2/5] ตรวจ/เริ่ม PostgreSQL และตัด session ของฐานข้อมูลอื่น
      [3/5] เริ่ม Odoo (venv19) แล้วรอจนพอร์ต HTTP ตอบสนอง
      [4/5] เริ่ม Nginx (port 80)
      [5/5] อัปเดต Cloudflare DDNS

    ข้อกำหนดของโปรเจกต์: ใช้ฐานข้อมูลเดียวคือ odoo19_pdev เท่านั้น

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File .\STEP-3-Start-Odoo19.ps1

.EXAMPLE
    # ใช้เมื่อถูกเรียกจาก STEP-ALL หรือ Task Scheduler (ไม่ต้องรอกด Enter)
    powershell -ExecutionPolicy Bypass -File .\STEP-3-Start-Odoo19.ps1 -NoPause
#>
param(
    [switch]$NoPause
)

$ErrorActionPreference = "Continue"   # ทำงานกับ service/process ภายนอก: จัดการ error แบบ explicit

# ===================== ค่าคงที่ของโปรเจกต์ =====================
$Root       = $PSScriptRoot
$TargetDb   = "^odoo19_p"                          # รูปแบบ DB ที่อนุญาต (regex: ขึ้นต้นด้วย odoo19_p)
$PgService  = "postgresql-x64-16"                  # PostgreSQL service เดียวที่เก็บไว้
$Config     = Join-Path $Root "odoo.conf"
$OdooLog    = Join-Path $Root "odoo_server.log"
$Python     = Join-Path $Root "venv19\Scripts\python.exe"
$OdooBin    = Join-Path $Root "odoo-bin"
$NginxDir   = Join-Path $Root "nginx\nginx-1.27.2"
$DdnsScript = Join-Path $Root "STEP-DDNS-Cloudflare-Odoo19.ps1"
$DdnsLog    = Join-Path $Root "ddns_update.log"
$TotalSteps = 5

function Write-Step([int]$No, [string]$Text) {
    Write-Host "`n[$No/$TotalSteps] $Text" -ForegroundColor Yellow
}

function Read-OdooConf {
    $values = @{}
    if (Test-Path -LiteralPath $Config) {
        foreach ($line in Get-Content -LiteralPath $Config) {
            if ($line -match '^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$') {
                $values[$Matches[1]] = $Matches[2].Trim()
            }
        }
    }
    return $values
}

function Get-PsqlPath {
    $pgRoot = Get-ChildItem 'C:\Program Files\PostgreSQL' -Directory -ErrorAction SilentlyContinue |
        Sort-Object Name -Descending | Select-Object -First 1
    if (-not $pgRoot) { return $null }
    $exe = Join-Path $pgRoot.FullName 'bin\psql.exe'
    if (Test-Path -LiteralPath $exe) { return $exe }
    return $null
}

function Test-Port([int]$Port) {
    # ตรวจ listening socket ที่ "มี process จริงเป็นเจ้าของ" เท่านั้น
    # หมายเหตุ 1: หลัง Stop-Process -Force Windows อาจทิ้ง ghost listener (OwningProcess = 0) ไว้ชั่วคราว
    #             ถ้านับ ghost ด้วยจะทำให้เข้าใจผิดว่าระบบยังรันอยู่ แล้วข้ามการ start → ระบบล่มเงียบ
    # หมายเหตุ 2: Get-NetTCPConnection -LocalPort อาจมองไม่เห็น listener บน [::] (dual-stack) จึง fallback netstat
    $real = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
            Where-Object { $_.OwningProcess -and $_.OwningProcess -ne 0 }
    if ($real) { return $true }
    $hit = netstat -ano | Select-String -Pattern ":$Port\s" | Select-String -Pattern "LISTENING" |
           Where-Object { $_ -notmatch "LISTENING\s+0\s*$" }
    return [bool]$hit
}

function Test-Http([string]$Url, [int]$TimeoutSec = 5) {
    # ตัวชี้วัดสุขภาพที่เชื่อถือได้จริง: มีอะไร "ตอบ HTTP 200" อยู่หรือไม่
    try {
        return ((Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec $TimeoutSec).StatusCode -eq 200)
    } catch {
        return $false
    }
}

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  STEP-3 : Start Odoo 19" -ForegroundColor Cyan
Write-Host "  Database : $TargetDb (pattern)" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

if (-not (Test-Path -LiteralPath $Python))  { Write-Host "[ERROR] ไม่พบ python ของ venv19: $Python" -ForegroundColor Red; if (-not $NoPause) { Read-Host "`nกด Enter เพื่อปิด" }; exit 1 }
if (-not (Test-Path -LiteralPath $OdooBin)) { Write-Host "[ERROR] ไม่พบ odoo-bin: $OdooBin" -ForegroundColor Red; if (-not $NoPause) { Read-Host "`nกด Enter เพื่อปิด" }; exit 1 }
if (-not (Test-Path -LiteralPath $Config))  { Write-Host "[ERROR] ไม่พบ odoo.conf: $Config" -ForegroundColor Red; if (-not $NoPause) { Read-Host "`nกด Enter เพื่อปิด" }; exit 1 }

$conf       = Read-OdooConf
$httpPort   = 8070
$geventPort = 8072
if ($conf.ContainsKey('http_port')   -and $conf['http_port'])   { $httpPort   = [int]$conf['http_port'] }
if ($conf.ContainsKey('gevent_port') -and $conf['gevent_port']) { $geventPort = [int]$conf['gevent_port'] }
$dbUser = 'odoo'
$dbPass = ''
if ($conf.ContainsKey('db_user'))     { $dbUser = $conf['db_user'] }
if ($conf.ContainsKey('db_password')) { $dbPass = $conf['db_password'] }

$exitCode = 0

# ==========================================================================
# 1. เคลียร์สิ่งที่ค้างอยู่และไม่ใช่ $TargetDb
# ==========================================================================
Write-Step 1 "เคลียร์ process / service ที่ค้างอยู่ (เก็บเฉพาะ $TargetDb)"

# 1a. ปิด Odoo server (python odoo-bin) ทุกตัวที่ยังรันอยู่
Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -eq "python.exe" -and $_.CommandLine -and $_.CommandLine -match "odoo-bin" } |
    ForEach-Object {
        Write-Host "  kill Odoo process PID $($_.ProcessId)" -ForegroundColor DarkYellow
        Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
    }

# 1b. ปิด process ที่ยังจับพอร์ต Odoo อยู่ (8069 legacy / http_port / gevent_port)
foreach ($port in @(8069, $httpPort, $geventPort) | Select-Object -Unique) {
    Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue |
        Select-Object -ExpandProperty OwningProcess -Unique |
        ForEach-Object {
            Write-Host "  kill process on port $port (PID $_)" -ForegroundColor DarkYellow
            Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue
        }
}

# 1c. ปิด nginx ที่ค้างอยู่ทั้งหมด ก่อนเริ่มใหม่ในขั้นตอนที่ 4 (กัน process สะสม)
#     nginx worker สืบทอด listening socket จาก master ถ้าฆ่าไม่ครบ port 80 จะยังค้าง
Get-Process nginx -ErrorAction SilentlyContinue | ForEach-Object {
    Write-Host "  kill nginx process PID $($_.Id)" -ForegroundColor DarkYellow
    Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
}
# รอจน nginx หายทั้งหมดจริง (สูงสุด 10 วินาที) ก่อนปล่อยให้ขั้นตอนถัดไปทำงาน
for ($i = 0; $i -lt 10; $i++) {
    if (-not (Get-Process nginx -ErrorAction SilentlyContinue)) { break }
    Start-Sleep -Seconds 1
}
$nginxLeft = Get-Process nginx -ErrorAction SilentlyContinue
if ($nginxLeft) { Write-Host "  เตือน: ยังมี nginx ค้างอยู่ (PID $(($nginxLeft.Id) -join ', '))" -ForegroundColor Yellow }
Start-Sleep -Seconds 2

# 1d. หยุด PostgreSQL service อื่นทั้งหมด (เช่น เวอร์ชัน 15 ของระบบเดิม)
Get-Service -Name "postgresql*" -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -ne $PgService -and $_.Status -eq "Running" } |
    ForEach-Object {
        Write-Host "  stop PostgreSQL service: $($_.Name)" -ForegroundColor DarkYellow
        Stop-Service -Name $_.Name -Force -ErrorAction SilentlyContinue
    }

Start-Sleep -Seconds 2

# 1e. หมุน log เก่า (ทำได้เฉพาะตอนนี้ เพราะ Odoo หยุดแล้ว)
#     บน Windows Odoo ใช้ logging.FileHandler จึงถือไฟล์ log เปิดไว้ตลอดเวลา
#     การ rename ไฟล์ขณะ Odoo รันจะล้มเหลว (file in use) จึงต้องหมุนตอนเริ่มระบบ
$LogDir      = Join-Path $Root "logs"
$LogRetainDays = 30
if (Test-Path -LiteralPath $OdooLog) {
    $logItem = Get-Item -LiteralPath $OdooLog -ErrorAction SilentlyContinue
    if ($logItem -and $logItem.Length -gt 0) {
        if (-not (Test-Path -LiteralPath $LogDir)) { New-Item -ItemType Directory -Path $LogDir -Force | Out-Null }
        $archive = Join-Path $LogDir ("odoo_server_{0}.log" -f (Get-Date -Format "yyyyMMdd_HHmmss"))
        Move-Item -LiteralPath $OdooLog -Destination $archive -Force
        Write-Host ("  หมุน log เก่า ({0:N0} KB) -> {1}" -f ($logItem.Length / 1KB), $archive) -ForegroundColor DarkYellow
        Get-ChildItem -LiteralPath $LogDir -Filter "odoo_server_*.log" -ErrorAction SilentlyContinue |
            Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-$LogRetainDays) } |
            ForEach-Object {
                Write-Host "  ลบ log เก่าเกิน $LogRetainDays วัน: $($_.Name)" -ForegroundColor DarkGray
                Remove-Item -LiteralPath $_.FullName -Force -ErrorAction SilentlyContinue
            }
    }
}

# ==========================================================================
# 2. ตรวจสอบ / เริ่ม PostgreSQL + ตัด session ของฐานข้อมูลอื่น
# ==========================================================================
Write-Step 2 "ตรวจ PostgreSQL ($PgService) และตัด session ของฐานข้อมูลอื่น"

$pg = Get-Service -Name $PgService -ErrorAction SilentlyContinue
if (-not $pg) {
    Write-Host "  ไม่พบ service '$PgService'" -ForegroundColor Red
    $exitCode = 1
} elseif ($pg.Status -eq "Running") {
    Write-Host "  PostgreSQL: Running" -ForegroundColor Green
} else {
    Write-Host "  กำลังเริ่ม PostgreSQL..." -ForegroundColor Yellow
    Start-Service -Name $PgService -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 3
    $pg = Get-Service -Name $PgService
    if ($pg.Status -eq "Running") { Write-Host "  PostgreSQL: Started" -ForegroundColor Green }
    else { Write-Host "  PostgreSQL: start ไม่สำเร็จ" -ForegroundColor Red; $exitCode = 1 }
}

$psql = Get-PsqlPath
if ($psql) {
    $env:PGPASSWORD = $dbPass
    $sql = "SELECT pg_terminate_backend(pid) FROM pg_stat_activity " +
           "WHERE datname IS NOT NULL AND datname !~ '$TargetDb' AND pid <> pg_backend_pid();"
    & $psql -U $dbUser -h localhost -d postgres -t -c $sql 2>$null | Out-Null
    Remove-Item Env:\PGPASSWORD -ErrorAction SilentlyContinue
    Write-Host "  ตัด session ของฐานข้อมูลอื่นแล้ว (เหลือเฉพาะ $TargetDb)" -ForegroundColor Green
} else {
    Write-Host "  ไม่พบ psql.exe - ข้ามการตัด session" -ForegroundColor Yellow
}

# ==========================================================================
# 3. เริ่ม Odoo
# ==========================================================================
Write-Step 3 "เริ่ม Odoo (port $httpPort)"

# ตัดสินจาก HTTP จริง (port อย่างเดียวเชื่อถือไม่ได้ เพราะอาจเป็น ghost listener ที่ PID = 0)
if (Test-Http "http://127.0.0.1:$httpPort/web/login") {
    Write-Host "  Odoo รันอยู่แล้วที่ port $httpPort" -ForegroundColor Green
} else {
    Write-Host "  กำลังเริ่ม Odoo..." -ForegroundColor Yellow
    # start แบบ detached (ไม่ตายเมื่อปิดหน้าต่าง console) เหมือน Nginx
    Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{
        CommandLine      = "`"$Python`" `"$OdooBin`" -c `"$Config`""
        CurrentDirectory = $Root
    } | Out-Null
    $timeout = 180
    $elapsed = 0
    $started = $false
    while ($elapsed -lt $timeout) {
        Start-Sleep -Seconds 3
        $elapsed += 3
        if (Test-Http "http://127.0.0.1:$httpPort/web/login" 10) { $started = $true; break }
    }
    if ($started) {
        Write-Host "  Odoo: Started (port $httpPort) ภายใน $elapsed วินาที" -ForegroundColor Green
    } else {
        Write-Host "  Odoo: ยังไม่ตอบสนองภายใน $timeout วินาที - ตรวจสอบ log: $OdooLog" -ForegroundColor Red
        $exitCode = 1
    }
}

# ==========================================================================
# 4. เริ่ม Nginx
# ==========================================================================
Write-Step 4 "เริ่ม Nginx (port 80)"

# ตัดสินจาก "process nginx" เป็นหลัก (port 80 อย่างเดียวเชื่อถือไม่ได้ เพราะ listener อาจอยู่บน [::])
$nginxExe  = Join-Path $NginxDir "nginx.exe"
$nginxProc = @(Get-Process nginx -ErrorAction SilentlyContinue)

if ($nginxProc.Count -gt 0) {
    Write-Host "  Nginx รันอยู่แล้ว ($($nginxProc.Count) process, port 80)" -ForegroundColor Green
} elseif (-not (Test-Path -LiteralPath $nginxExe)) {
    Write-Host "  ไม่พบ Nginx ที่ $NginxDir - ข้ามขั้นตอนนี้" -ForegroundColor Yellow
} else {
    Write-Host "  กำลังเริ่ม Nginx..." -ForegroundColor Yellow
    # start แบบ detached (ไม่ตายเมื่อปิดหน้าต่าง console)
    Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{
        CommandLine      = "`"$nginxExe`""
        CurrentDirectory = $NginxDir
    } | Out-Null
    # รอจน nginx ทำงานจริง (มี process + เปิด port 80) สูงสุด 15 วินาที
    $nginxOk = $false
    for ($i = 0; $i -lt 5; $i++) {
        Start-Sleep -Seconds 3
        if ((Get-Process nginx -ErrorAction SilentlyContinue) -and (Test-Port 80)) { $nginxOk = $true; break }
    }
    if ($nginxOk) {
        Write-Host "  Nginx: Started (port 80)" -ForegroundColor Green
    } else {
        # รายงาน process ที่ยังจับ port 80 อยู่ เพื่อช่วยวินิจฉัย socket ค้าง
        $holder = (Get-NetTCPConnection -LocalPort 80 -State Listen -ErrorAction SilentlyContinue |
                   Select-Object -ExpandProperty OwningProcess -Unique) -join ', '
        if (-not $holder) { $holder = "(ไม่พบ process จับ port)" }
        Write-Host "  Nginx: start ไม่สำเร็จ (port 80 ถูกจับโดย PID $holder)" -ForegroundColor Red
        $exitCode = 1
    }
}

# ==========================================================================
# 5. อัปเดต Cloudflare DNS (DDNS)
# ==========================================================================
Write-Step 5 "อัปเดต Cloudflare DDNS"

if (Test-Path -LiteralPath $DdnsScript) {
    & powershell -NoProfile -ExecutionPolicy Bypass -File $DdnsScript
    Write-Host "  DDNS: เสร็จสิ้น (log: $DdnsLog)" -ForegroundColor Green
} else {
    Write-Host "  ไม่พบสคริปต์ DDNS: $DdnsScript - ข้ามขั้นตอนนี้" -ForegroundColor Yellow
}

# ==========================================================================
# สรุปผล
# ==========================================================================
Write-Host "`n========================================" -ForegroundColor Cyan
if ($exitCode -eq 0) { Write-Host "  STEP-3 เสร็จสิ้นสมบูรณ์" -ForegroundColor Green }
else { Write-Host "  STEP-3 เสร็จสิ้น แต่มีบางขั้นตอนล้มเหลว" -ForegroundColor Red }
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Local    : http://localhost:$httpPort/web" -ForegroundColor White
Write-Host "  Network  : http://172.20.1.166:$httpPort/web" -ForegroundColor White
Write-Host "  Internet : https://pdev-erp.auto-info.com" -ForegroundColor White
Write-Host "  Odoo log : $OdooLog" -ForegroundColor Gray
Write-Host "  DDNS log : $DdnsLog" -ForegroundColor Gray

if (-not $NoPause) { Read-Host "`nกด Enter เพื่อปิดหน้าต่างนี้" }
exit $exitCode
