# =============================================================================
# ci-check.ps1 - Local runner mirroring GitHub Actions CI pipeline.
# Cleaned & fixed: Corrected execution tracking, scope safety, and temp cleanup.
# =============================================================================

param(
    [switch]$KeepDb,
    [switch]$SkipSlow,
    [string]$DbName = "ci",
    [double]$CoverageMin = 60.0
)

$ErrorActionPreference = "Stop"

# --- Paths & Config -----------------------------------------------------------
$pythonExe = ".\venv\Scripts\python.exe"
$testLog = ".\odoo-test.log"
$dbHost = if ($env:PGHOST) { $env:PGHOST } else { "localhost" }
$dbPort = if ($env:PGPORT) { $env:PGPORT } else { 5432 }
$dbUser = if ($env:PGUSER) { $env:PGUSER } else { "odoo" }
$dbPassword = if ($env:PGPASSWORD) { $env:PGPASSWORD } else { "odoo" }
$addonsPath = "addons,custom_addons"

$failed = $false
$stageFails = @()

function Write-Step([string]$message) {
    Write-Host ""
    Write-Host "==> $message" -ForegroundColor Cyan
}

function Fail-Step([string]$message) {
    Write-Host "    FAIL: $message" -ForegroundColor Red
    $script:stageFails += $message
    $script:failed = $true
}

function Test-CommandExists([string]$name) {
    return $null -ne (Get-Command $name -ErrorAction SilentlyContinue)
}

# --- Safe Temporary Python Runner ---------------------------------------------
$tmpScripts = Join-Path $env:TEMP "ci-check-py"

function Invoke-PyScript {
    param(
        [string[]]$Lines,
        [string]$Name,
        [string[]]$PyArgs = @()
    )
    $file = Join-Path $tmpScripts "$Name-$([Guid]::NewGuid().ToString().Substring(0,8)).py"
    New-Item -ItemType Directory -Path $tmpScripts -Force | Out-Null
    
    try {
        Set-Content -Path $file -Value $Lines -Encoding utf8
        $output = & $pythonExe $file $PyArgs 2>&1
        return $output
    }
    finally {
        if (Test-Path $file) { Remove-Item $file -Force }
    }
}

# =============================================================================
# JOB 1: Terraform (fast)
# =============================================================================
Write-Step "JOB terraform: fmt / init / validate"

if (-not (Test-CommandExists "terraform")) {
    Fail-Step "terraform CLI not found on PATH - install it (CI uses 1.9)"
}
else {
    # Suppress native stderr crashing PS 5.1 across all native terraform commands
    $prevEap = $ErrorActionPreference
    $ErrorActionPreference = "Continue"

    # 1. fmt check (use '.' because -chdir already changed working directory)
    & terraform -chdir=infra/terraform/ fmt -check -recursive . 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Fail-Step "terraform fmt -check failed - run: terraform -chdir=infra/terraform/ fmt -recursive ."
    }
    else { Write-Host "    fmt OK" -ForegroundColor Green }

    # 2. init check
    & terraform -chdir=infra/terraform/ init -backend=false 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Fail-Step "terraform init failed"
    }
    else { Write-Host "    init OK" -ForegroundColor Green }

    # 3. validate check
    & terraform -chdir=infra/terraform/ validate 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Fail-Step "terraform validate failed"
    }
    else { Write-Host "    validate OK" -ForegroundColor Green }

    $ErrorActionPreference = $prevEap
}

# =============================================================================
# JOB 3: Linting
# =============================================================================
Write-Step "JOB lint: ruff check + format (custom_addons/invoice_agent)"

if (-not (Test-CommandExists "ruff")) {
    Fail-Step "ruff not found on PATH - pip install ruff"
}
else {
    $ruffCheckFailed = $false
    & ruff check custom_addons/invoice_agent --config pyproject.toml
    if ($LASTEXITCODE -ne 0) {
        Fail-Step "ruff check failed (invoice_agent)"
        $ruffCheckFailed = $true
    }
    
    & ruff format custom_addons/invoice_agent --config pyproject.toml --check
    if ($LASTEXITCODE -ne 0) {
        Fail-Step "ruff format --check failed (invoice_agent)"
        $ruffCheckFailed = $true
    }

    if (-not $ruffCheckFailed) {
        Write-Host "    ruff OK" -ForegroundColor Green
    }
}

# =============================================================================
# JOB 5a: Bandit SAST (fast)
# =============================================================================
Write-Step "JOB security: bandit (addon + invoice-ai)"

if (-not (Test-CommandExists "bandit")) {
    Fail-Step "bandit not found on PATH - pip install 'bandit[toml]'"
}
else {
    $prevEap = $ErrorActionPreference
    $ErrorActionPreference = "Continue"

    # Addon check
    & bandit -r custom_addons/invoice_agent/ --severity-level medium -f json -o bandit-addon.json 2>$null
    & bandit -r custom_addons/invoice_agent/ --severity-level medium -f screen -q
    if ($LASTEXITCODE -ne 0) {
        Fail-Step "bandit found medium+ issues in custom_addons/invoice_agent/"
    }
    else { Write-Host "    addon clean" -ForegroundColor Green }

    # AI app check
    & bandit -r invoice-ai/app/ --severity-level medium -f json -o bandit-ai.json 2>$null
    & bandit -r invoice-ai/app/ --severity-level medium -f screen -q
    if ($LASTEXITCODE -ne 0) {
        Fail-Step "bandit found medium+ issues in invoice-ai/app/"
    }
    else { Write-Host "    invoice-ai clean" -ForegroundColor Green }

    $ErrorActionPreference = $prevEap
}
# =============================================================================
# JOB 5b: Trivy Filesystem Scan
# =============================================================================
Write-Step "JOB security: trivy filesystem scan"

if (-not (Test-CommandExists "trivy")) {
    Fail-Step "trivy not found on PATH"
}
else {
    $prevEap = $ErrorActionPreference
    $ErrorActionPreference = "Continue"

    # Added --timeout 10m and --skip-dirs addons to prevent scanning base Odoo core
    & trivy fs --severity CRITICAL,HIGH --ignore-unfixed --exit-code 1 --quiet --timeout 10m --skip-dirs addons .
    if ($LASTEXITCODE -ne 0) { 
        Fail-Step "trivy fs found CRITICAL/HIGH vulnerabilities" 
    } 
    else { 
        Write-Host "    fs scan clean" -ForegroundColor Green 
    }

    $ErrorActionPreference = $prevEap
}

# =============================================================================
# JOB 5c: Disaster Recovery Runbook Check
# =============================================================================
Write-Step "JOB security: DR runbook age check (< 90 days)"

$runbook = "docs/runbooks/disaster-recovery.md"
if (-not (Test-Path $runbook)) {
    Fail-Step "$runbook is missing!"
}
else {
    $ageDays = [int]((New-TimeSpan (Get-Item $runbook).LastWriteTime (Get-Date)).TotalDays)
    Write-Host "    DR runbook age: $ageDays days"
    if ($ageDays -gt 90) {
        Fail-Step "DR runbook older than 90 days - re-run restore drill"
    }
    else { Write-Host "    runbook fresh" -ForegroundColor Green }
}
# =============================================================================
# JOB 2: Observability
# =============================================================================
Write-Step "JOB observability: prometheus / alertmanager / grafana configs"

if (-not (Test-CommandExists "docker")) {
    Fail-Step "docker not available - start Docker Desktop"
}
else {
    $prevEap = $ErrorActionPreference
    $ErrorActionPreference = "Continue"

    $pwdPath = (Get-Location).Path.Replace('\', '/')

    & docker run --rm --entrypoint /bin/promtool -v "${pwdPath}/infra/observability/prometheus:/etc/prometheus" `
        prom/prometheus:v2.53.0 check config /etc/prometheus/prometheus.yml 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) { Fail-Step "prometheus config invalid" } 
    else { Write-Host "    prometheus OK" -ForegroundColor Green }

    & docker run --rm --entrypoint /bin/amtool -v "${pwdPath}/infra/observability/alertmanager:/etc/alertmanager" `
        prom/alertmanager:v0.27.0 check-config /etc/alertmanager/alertmanager.yml 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) { Fail-Step "alertmanager config invalid" } 
    else { Write-Host "    alertmanager OK" -ForegroundColor Green }

    $grafana = Invoke-PyScript -Name "grafana_json" -Lines @(
        'import json'
        'json.load(open("infra/observability/grafana/dashboards/agent-slo.json"))'
        'print("OK")'
    )
    if ($grafana -ne "OK") { Fail-Step "grafana dashboard JSON invalid: $grafana" } 
    else { Write-Host "    grafana dashboard JSON OK" -ForegroundColor Green }

    $ErrorActionPreference = $prevEap
}
# --- Fast-fail gate -----------------------------------------------------------
if ($failed) {
    Write-Host ""
    Write-Host "=== FAST CHECKS FAILED ===" -ForegroundColor Red
    foreach ($s in $stageFails) { Write-Host "  - $s" -ForegroundColor Red }
    exit 1
}

if ($SkipSlow) {
    Write-Host ""
    Write-Host "=== FAST CHECKS PASSED (-SkipSlow active) ===" -ForegroundColor Green
    exit 0
}

# =============================================================================
# JOB 4: Odoo Unit Tests & Coverage
# =============================================================================
Write-Step "Preflight: virtualenv, CI dependencies, Postgres"

if (-not (Test-Path $pythonExe)) {
    Fail-Step "virtualenv missing at $pythonExe"
}

$ciDeps = @("anthropic", "pydantic", "pytesseract", "pdf2image", "boto3", "coverage", "pypdf", "PIL", "fitz", "requests")
foreach ($dep in $ciDeps) {
    & $pythonExe -c "import $dep" 2>$null
    if ($LASTEXITCODE -ne 0) { Fail-Step "missing required dependency: '$dep'" }
}

if (-not $failed) {
    $pgOk = Invoke-PyScript -Name "postgres_probe" -Lines @(
        'import psycopg2, sys'
        'try:'
        '    c = psycopg2.connect(host=sys.argv[1], port=int(sys.argv[2]), user=sys.argv[3], password=sys.argv[4], dbname="postgres")'
        '    c.close()'
        '    print("OK")'
        'except Exception as e:'
        '    print("ERR: %s" % e)'
    ) -PyArgs @($dbHost, $dbPort, $dbUser, $dbPassword)

    if ($pgOk -ne "OK") { Fail-Step "Postgres ping failed: $pgOk" } 
    else { Write-Host "    Postgres connection established" -ForegroundColor Green }
}

if ($failed) { exit 1 }

# --- Database Management -----------------------------------------------------
$dbArgs = @($dbHost, $dbPort, $dbUser, $dbPassword, $DbName)

if ($KeepDb) {
    Write-Host "==> Reusing database '$DbName'" -ForegroundColor Yellow
}
else {
    Write-Step "Database: dropping existing '$DbName' for clean state"
    $resetOut = Invoke-PyScript -Name "drop_db" -PyArgs $dbArgs -Lines @(
        'import sys, psycopg2'
        'HOST, PORT, USER, PWD, DB = sys.argv[1:6]'
        'conn = psycopg2.connect(host=HOST, port=int(PORT), user=USER, password=PWD, dbname="postgres")'
        'conn.autocommit = True'
        'cur = conn.cursor()'
        'cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (DB,))'
        'if cur.fetchone():'
        '    cur.execute("DROP DATABASE %s" % DB)'
        '    print("dropped %s" % DB)'
        'else:'
        '    print("no existing %s" % DB)'
    )
    if ($resetOut -match "Error|Traceback|refused") {
        Fail-Step "Failed to reset database '$DbName': $resetOut"
        exit 1
    }
}

# --- Test Execution -----------------------------------------------------------
Write-Step "Running Odoo test suite under Coverage"

$procInfo = New-Object System.Diagnostics.ProcessStartInfo
$procInfo.FileName = (Resolve-Path $pythonExe).Path
$procInfo.Arguments = "-m coverage run --concurrency=thread --source=custom_addons/invoice_agent odoo-bin -d $DbName -i invoice_agent --addons-path=$addonsPath --test-enable --test-tags /invoice_agent --stop-after-init --log-level=test --db_host=$dbHost --db_port=$dbPort --db_user=$dbUser --db_password=$dbPassword"
$procInfo.RedirectStandardOutput = $true
$procInfo.RedirectStandardError = $true
$procInfo.UseShellExecute = $false

$proc = New-Object System.Diagnostics.Process
$proc.StartInfo = $procInfo

$logWriter = [System.IO.StreamWriter]::new((Resolve-Path .).Path + "\" + $testLog, $false)

$proc.Add_OutputDataReceived({
        if ($_.Data) { 
            $global:logWriter.WriteLine($_.Data)
            Write-Host $_.Data
        }
    })
$proc.Add_ErrorDataReceived({
        if ($_.Data) { 
            $global:logWriter.WriteLine($_.Data)
            Write-Host $_.Data
        }
    })

$proc.Start() | Out-Null
$proc.BeginOutputReadLine()
$proc.BeginErrorReadLine()
$proc.WaitForExit()
$logWriter.Close()

if ($proc.ExitCode -ne 0) {
    Fail-Step "Odoo test process exited with code $($proc.ExitCode) - see $testLog"
}

# --- Log Verification --------------------------------------------------------
Write-Step "Analyzing logs for test execution integrity"

$postTestLine = Select-String -Path $testLog -Pattern 'post-tests in (\d+)\.\d+s' | Select-Object -First 1
if ($postTestLine -and $postTestLine.Matches[0].Groups[1].Value -eq "0") {
    Fail-Step "0 post_install tests executed. DB state was likely dirty. Run without -KeepDb."
}
elseif (-not $postTestLine) {
    Fail-Step "Could not find post-test completion summary in $testLog"
}

$problems = Select-String -Path $testLog -Pattern 'FAIL|ERROR|CRITICAL' | Where-Object { $_.Line -notmatch '\([A-Z]+/[0-9]+\)' }
if ($problems) {
    foreach ($p in $problems) { Write-Host "    $($p.Line)" -ForegroundColor Red }
    Fail-Step "Unfiltered FAIL/ERROR/CRITICAL markers found in logs"
}
else {
    Write-Host "    Log inspection clean" -ForegroundColor Green
}

# --- Coverage Gates -----------------------------------------------------------
Write-Step "Evaluating Coverage metrics (min target: ${CoverageMin}%)"

if (-not (Test-Path ".\.coverage")) {
    Fail-Step "Coverage session state file standard (.coverage) missing"
}
else {
    & $pythonExe -m coverage report -m
    & $pythonExe -m coverage xml -o coverage.xml
    
    $report = & $pythonExe -m coverage report
    $totalLine = $report | Select-String '^TOTAL' | Select-Object -First 1
    if ($totalLine) {
        $total = [double](($totalLine.Line.Trim() -split '\s+' | Select-Object -Last 1).TrimEnd('%'))
        Write-Host "    Calculated Coverage: $total%" -ForegroundColor Yellow
        if ($total -lt $CoverageMin) {
            Fail-Step "Coverage gate failure: $total% < required target $CoverageMin%"
        }
        else {
            Write-Host "    Coverage gate passed" -ForegroundColor Green
        }
    }
    else {
        Fail-Step "Could not parse TOTAL metrics from coverage output"
    }
}

# =============================================================================
# JOB 5d: Trivy Container Scan
# =============================================================================
Write-Step "JOB security: trivy image scan"

if (Test-CommandExists "trivy" -and Test-CommandExists "docker") {
    $prevEap = $ErrorActionPreference
    $ErrorActionPreference = "Continue"

    & docker build -t invoice-ai:security-scan ./invoice-ai 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Fail-Step "docker build ./invoice-ai failed"
    }
    else {
        & trivy image --severity CRITICAL,HIGH --ignore-unfixed --exit-code 1 --quiet invoice-ai:security-scan
        if ($LASTEXITCODE -ne 0) { Fail-Step "trivy image vulnerabilities found" }
        else { Write-Host "    image scan clean" -ForegroundColor Green }
    }

    $ErrorActionPreference = $prevEap
}

# =============================================================================
# Final Summary
# =============================================================================
Write-Host ""
if ($failed) {
    Write-Host "=== CI CHECKS FAILED ===" -ForegroundColor Red
    foreach ($s in $stageFails) { Write-Host "  - $s" -ForegroundColor Red }
    exit 1
}

Write-Host "=== ALL CI CHECKS PASSED ===" -ForegroundColor Green
exit 0