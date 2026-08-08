# =============================================================================
# ci-check.ps1 - Run the EXACT GitHub Actions CI checks locally, before pushing.
#
# Mirrors .github/workflows/ci.yml (job: test):
#
#   1. Preflight  - venv + the exact pip deps CI installs
#   2. Database   - reuse the local `ci` DB, or drop it first for full parity
#                   (CI runs on a pristine Postgres container every time)
#   3. Run tests  - coverage run --concurrency=thread --source=custom_addons/invoice_agent
#                   odoo-bin -d ci -i invoice_agent --addons-path=addons,custom_addons
#                   --test-enable --test-tags /invoice_agent --stop-after-init
#                   --log-level=test --db_host=localhost --db_port=5432
#                   --db_user=odoo --db_password=odoo
#   4. Log gate   - fail on FAIL/ERROR/CRITICAL lines, ignoring benign Odoo
#                   noise like "(WARNING/x)" counters (same regex as CI)
#   5. Coverage   - require >= COVERAGE_MIN (CI gate: 60%) on invoice_agent
#
# Usage (from repo root):
#   .\bashs\ci-check.ps1              # run against existing `ci` DB (fast, repeatable)
#   .\bashs\ci-check.ps1 -ResetDb     # drop `ci` first - exact CI parity
#   .\bashs\ci-check.ps1 -CoverageMin 70   # raise the gate
#
# Exit code 0 -> safe to push.  Non-zero -> the same failure CI would report.
#
# NOTE: this file is intentionally pure ASCII. Windows PowerShell 5.1 reads
# .ps1 files as ANSI unless a BOM is present, and UTF-8 em-dashes/arrows
# corrupt the tokenizer. Keep it ASCII.
# =============================================================================

# CI always runs on a FRESH Postgres (new container per run). If we reuse an
# existing `ci` DB where invoice_agent is already installed, Odoo skips the
# whole post_install test suite ("0 post-tests") and the results stop
# matching GitHub Actions. So by default we DROP the DB to mirror CI exactly.
# Pass -KeepDb to reuse an existing DB deliberately (fast iteration, but the
# result is NOT a valid CI prediction - a zero-test guard is enforced below).
param(
    [switch]$KeepDb,
    [string]$DbName = "ci",
    [double]$CoverageMin = 60.0
)

$ErrorActionPreference = "Stop"

# --- Paths (relative to repo root, like start-odoo.ps1) ---------------------
$pythonExe = ".\venv\Scripts\python.exe"
$testLog = ".\odoo-test.log"
$dbHost = "localhost"
$dbPort = 5432
$dbUser = "odoo"
$dbPassword = "odoo"

# CI's exact module list from the "Install Python Dependencies" step.
$ciDeps = @(
    "anthropic", "pydantic", "pytesseract", "pdf2image", "boto3", "coverage"
)

# --addons-path value kept in a variable so no formatter can inject a space
# into the flag (a space here would split the comma list into two args).
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

# --- Python snippets run from temp files -------------------------------------
# PowerShell 5.1 strips embedded double quotes when passing `-c` code to a
# native exe (`print("x")` arrives as `print(x)`). Writing the snippet to a
# temp file and executing it avoids that entirely.
$tmpScripts = Join-Path $env:TEMP "ci-check-py"

function Invoke-PyScript {
    # NOTE: parameter is named $PyArgs, never $Args — $Args is a PowerShell
    # automatic variable and shadowing it breaks parameter binding.
    param(
        [string[]]$Lines,
        [string]$Name,
        [string[]]$PyArgs = @()
    )
    $file = Join-Path $tmpScripts "$Name.py"
    New-Item -ItemType Directory -Path $tmpScripts -Force | Out-Null
    Set-Content -Path $file -Value $Lines -Encoding utf8
    $output = & $pythonExe $file $PyArgs 2>&1
    $code = $LASTEXITCODE
    Remove-Item $file -Force
    return $output
}

# =============================================================================
# 1. Preflight - venv, deps, Postgres
# =============================================================================
Write-Step "Preflight: virtualenv, CI dependencies, Postgres"

if (-not (Test-Path $pythonExe)) {
    Fail-Step "virtualenv not found at $pythonExe - create it with:  python -m venv venv"
}
else {
    Write-Host "    venv OK: $pythonExe" -ForegroundColor Green
}

if (-not $failed) {
    foreach ($dep in $ciDeps) {
        & $pythonExe -c "import $dep" 2>$null
        if ($LASTEXITCODE -ne 0) {
            Fail-Step "missing pip package '$dep' - install CI deps:"
            Write-Host "        .\venv\Scripts\python.exe -m pip install -r custom_addons/invoice_agent/requirements.txt coverage"
        }
    }
    if (-not $failed) { Write-Host "    CI dependencies OK" -ForegroundColor Green }
}

if (-not $failed) {
    $pgOk = Invoke-PyScript -Name "postgres_probe" -Lines @(
        'import psycopg2'
        'try:'
        '    c = psycopg2.connect(host="localhost", port=5432, user="odoo", password="odoo", dbname="postgres")'
        '    c.close()'
        '    print("OK")'
        'except Exception as e:'
        '    print("ERR: %s" % e)'
    )
    if ($pgOk -ne "OK") {
        Fail-Step "cannot reach Postgres as odoo/odoo@localhost:5432: $pgOk"
    }
    else {
        Write-Host "    Postgres OK (odoo/odoo@localhost:5432)" -ForegroundColor Green
    }
}

if ($failed) {
    Write-Host ""
    Write-Host "Preflight failed - fix the issues above, then re-run." -ForegroundColor Red
    exit 1
}

# =============================================================================
# 2. Database - CI uses a fresh `ci` DB. -ResetDb gives the same guarantee.
# =============================================================================
$dbArgs = @($dbHost, $dbPort, $dbUser, $dbPassword, $DbName)

$resetOut = $null
if ($KeepDb) {
    # Deliberate fast iteration. A zero-test guard later fails loudly if the
    # reused DB skipped the suite, so this can never silently pass.
    $exists = Invoke-PyScript -Name "db_exists" -PyArgs $dbArgs -Lines @(
        'import sys, psycopg2'
        'HOST, PORT, USER, PWD, DB = sys.argv[1:6]'
        'conn = psycopg2.connect(host=HOST, port=int(PORT), user=USER, password=PWD, dbname="postgres")'
        'cur = conn.cursor()'
        'cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (DB,))'
        'print("yes" if cur.fetchone() else "no")'
    )
    if ($exists -eq "yes") {
        Write-Host ""
        Write-Host "==> Reusing existing '$DbName' DB (WARNING: CI runs on a fresh DB; if invoice_agent is already installed here, 0 tests will run and the check will FAIL below)" -ForegroundColor Yellow
    }
    else {
        Write-Host ""
        Write-Host "==> '$DbName' will be created by Odoo, like CI" -ForegroundColor Cyan
    }
}
else {
    # Default: mirror CI exactly - fresh database every run.
    Write-Step "Database: dropping existing '$DbName' for pristine CI parity (CI uses a fresh Postgres container)"
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
        Fail-Step "could not drop '$DbName' - is another Odoo process connected to it?"
        Write-Host "The same failures would appear in GitHub Actions. Fix them, re-run, then push." -ForegroundColor Red
        exit 1
    }
}

# =============================================================================
# 3. Run Odoo tests under coverage - the CI command
# =============================================================================
Write-Step "Running Odoo tests (this is the CI command, takes a few minutes)"

# PS 5.1 + EAP=Stop treats stderr from a native exe as a terminating error
# and kills the run on Odoo's first log line. Run the pipeline in a child
# scope with EAP=Continue so stderr merges into the log and the process
# completes; capture its real exit code separately.
$odooNativeExit = $null
& {
    $prevEap = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        & $pythonExe -m coverage run --concurrency=thread --source=custom_addons/invoice_agent `
            odoo-bin -d $DbName -i invoice_agent --addons-path=$addonsPath `
            --test-enable --test-tags /invoice_agent --stop-after-init `
            --log-level=test --db_host=$dbHost --db_port=$dbPort `
            --db_user=$dbUser --db_password=$dbPassword 2>&1 |
        Tee-Object -FilePath $testLog
    }
    finally {
        $script:odooNativeExit = $LASTEXITCODE
        $ErrorActionPreference = $prevEap
    }
}

if ($null -ne $odooNativeExit -and $odooNativeExit -ne 0) {
    Fail-Step "Odoo process exited with code $odooNativeExit - see $testLog"
}

# =============================================================================
# 3b. Zero-test guard - a run where the post_install suite did not execute is
#     NOT a valid CI prediction (CI always re-installs on a fresh DB and runs
#     the full /invoice_agent tag). Catch that BEFORE trusting the gates below.
# =============================================================================
$postTestLine = Select-String -Path $testLog -Pattern 'post-tests in (\d+)\.\d+s' |
Select-Object -First 1
if ($postTestLine -and $postTestLine.Matches[0].Groups[1].Value -eq "0") {
    Fail-Step "0 post_install tests ran - a reused DB with the module already installed skips the suite (CI always runs on a fresh DB). Delete the 'ci' DB or run without -KeepDb."
}
elseif (-not $postTestLine) {
    # Fail-safe: if the log has no summary line at all, we cannot prove tests ran.
    Fail-Step "could not find the Odoo test summary in $testLog - cannot verify tests executed"
}

# =============================================================================
# 4. Log gate - mirror CI:
#    grep -E 'FAIL|ERROR|CRITICAL' | grep -vE '\([A-Z]+/[0-9]+\)'
# =============================================================================
Write-Step "Scanning odoo-test.log for real failures"

$problems = Select-String -Path $testLog -Pattern 'FAIL|ERROR|CRITICAL' |
Where-Object { $_.Line -notmatch '\([A-Z]+/[0-9]+\)' }

if ($problems) {
    foreach ($p in $problems) { Write-Host "    $($p.Line)" -ForegroundColor Red }
    Fail-Step "FAIL/ERROR/CRITICAL lines found in test log (filtered like CI)"
}
else {
    Write-Host "    No genuine failures in test log" -ForegroundColor Green
}

# =============================================================================
# 5. Coverage gate - CI: coverage report + COVERAGE_MIN=60
# =============================================================================
Write-Step "Coverage report and gate (min ${CoverageMin}%)"

if (-not (Test-Path ".\.coverage")) {
    Fail-Step "No .coverage file found on disk - tests did not run under coverage"
}
else {
    & $pythonExe -m coverage report -m
    if ($LASTEXITCODE -ne 0) {
        Fail-Step "coverage report failed"
    }
    & $pythonExe -m coverage xml -o coverage.xml
    if ($LASTEXITCODE -ne 0) {
        Fail-Step "coverage xml export failed"
    }

    $report = & $pythonExe -m coverage report
    $totalLine = $report | Select-String '^TOTAL' | Select-Object -First 1
    if (-not $totalLine) {
        Fail-Step "could not extract coverage total from coverage report"
    }
    else {
        # coverage prints "18%" — strip the '%' suffix before parsing.
        $total = [double](($totalLine.Line.Trim() -split '\s+' | Select-Object -Last 1).TrimEnd('%'))
        Write-Host ""
        Write-Host "    invoice_agent total coverage: $total%" -ForegroundColor Yellow
        if ($total -lt $CoverageMin) {
            Fail-Step "coverage gate failed: $total% is below the required $CoverageMin%"
        }
        else {
            Write-Host "    Coverage gate passed: $total% >= $CoverageMin%" -ForegroundColor Green
        }
    }
}

# =============================================================================
# Summary
# =============================================================================
Write-Host ""
if ($failed) {
    Write-Host "=== CI CHECK FAILED ===" -ForegroundColor Red
    foreach ($s in $stageFails) { Write-Host "  - $s" -ForegroundColor Red }
    Write-Host "The same failures would appear in GitHub Actions. Fix them, re-run, then push."
    Write-Host "Full test output: $testLog"
    exit 1
}

Write-Host "=== CI CHECK PASSED - safe to push ===" -ForegroundColor Green
Write-Host "Full test output: $testLog"
Write-Host "Coverage report:  coverage.xml"
exit 0
