﻿<#
.SYNOPSIS
    รัน unit test ของโมดูล Odoo 19 บน data-dir แยก (isolated) เพื่อผลลัพธ์ที่ deterministic

.DESCRIPTION
    ปัญหาเดิม: session store ที่ (data_dir)\sessions มี shard บางโฟลเดอร์ที่เขียนไม่ได้
    (ACL/owner mismatch บน Windows) ทำให้ session บางครั้งหายไป -> เกิด "Session expired"
    แบบสุ่มในชุดเทสต์ HttpCase

    สคริปต์นี้จึงบังคับให้การรันเทสต์ใช้ --data-dir แยกจากระบบจริง (ค่าเริ่มต้น data_test)
    เพื่อให้ session store สะอาดและแยกขาดจาก dev/production จึงรันซ้ำได้ผลเดิมเสมอ

    ค่าอื่น ๆ (db_name ฯลฯ) อ่านจาก odoo.conf โดยอัตโนมัติ
    ข้อกำหนด: ต้องไม่มี Odoo server ตัวอื่นจับพอร์ตเทสต์อยู่

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File .\run-tests.ps1 -Module od19_website

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File .\run-tests.ps1 -Module od19_approval_center,od19_website

.EXAMPLE
    # ล้าง session store แยกก่อนรัน เพื่อเริ่มจากศูนย์
    powershell -ExecutionPolicy Bypass -File .\run-tests.ps1 -Module od19_website -Clean
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string[]]$Module,

    [string]$Database,
    [string]$DataDir,
    [int]$HttpPort = 8075,
    [string]$LogFile,
    [switch]$Clean
)

$ErrorActionPreference = 'Stop'

$Root    = $PSScriptRoot
$Config  = Join-Path $Root 'odoo.conf'
$Python  = Join-Path $Root 'venv19\Scripts\python.exe'
$OdooBin = Join-Path $Root 'odoo-bin'
$sep     = '=' * 64

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
$conf = Read-OdooConf

if (-not $Database) { $Database = if ($conf['db_name']) { $conf['db_name'] } else { 'odoo19_pdev' } }
if (-not $DataDir) { $DataDir = Join-Path $Root 'data_test' }
if (-not $LogFile) { $LogFile = Join-Path $Root 'data_test_run.log' }

$testTags = ($Module | ForEach-Object { '/' + $_ }) -join ','

Write-Host $sep
Write-Host ' Odoo 19 - isolated test run' -ForegroundColor Cyan
Write-Host $sep
Write-Host ("  modules   : {0}" -f ($Module -join ', '))
Write-Host ("  test-tags : {0}" -f $testTags)
Write-Host ("  database  : {0}" -f $Database)
Write-Host ("  data-dir  : {0}" -f $DataDir)
Write-Host ("  http-port : {0}" -f $HttpPort)
Write-Host ("  log       : {0}" -f $LogFile)

foreach ($p in @($Python, $OdooBin, $Config)) {
    if (-not (Test-Path -LiteralPath $p)) { throw "ไม่พบไฟล์ที่จำเป็น: $p" }
}

$busy = Get-NetTCPConnection -State Listen -LocalPort $HttpPort -ErrorAction SilentlyContinue
if ($busy) {
    throw ("พอร์ต {0} ถูกใช้อยู่ (pid {1}) — ปิด server ตัวนั้น หรือใช้ -HttpPort อื่น" -f $HttpPort, $busy[0].OwningProcess)
}

if (-not (Test-Path -LiteralPath $DataDir)) {
    New-Item -ItemType Directory -Path $DataDir -Force | Out-Null
    Write-Host ("  created data-dir: {0}" -f $DataDir) -ForegroundColor DarkGray
}
if ($Clean) {
    $sess = Join-Path $DataDir 'sessions'
    if (Test-Path -LiteralPath $sess) {
        Remove-Item -LiteralPath $sess -Recurse -Force
        Write-Host '  cleared isolated session store (-Clean)' -ForegroundColor DarkGray
    }
}

$odooArgs = @(
    $OdooBin, '-c', $Config,
    '-d', $Database,
    '-u', ($Module -join ','),
    '--data-dir', $DataDir,
    '--http-port', $HttpPort,
    '--test-enable',
    '--test-tags', $testTags,
    '--stop-after-init',
    '--logfile', $LogFile
)
Write-Host "`n> $Python $($odooArgs -join ' ')" -ForegroundColor DarkGray
& $Python @odooArgs
$code = $LASTEXITCODE

Write-Host "`n$sep"
$result = Select-String -LiteralPath $LogFile -Pattern 'tests\.result:.*?of \d+ tests' -ErrorAction SilentlyContinue |
    Select-Object -Last 1
if ($result) {
    Write-Host ("  {0}" -f $result.Line.Trim()) -ForegroundColor Green
} else {
    Write-Host '  ไม่พบสรุปผลใน log — เปิดดู log เพื่อตรวจสอบ' -ForegroundColor Yellow
}
Write-Host ("  exit code : {0}" -f $code)
Write-Host $sep

exit $code
