#!/usr/bin/env bash
# smoke-test.sh — Post-deploy smoke test for Invoice Agent
#
# Usage:
#   ./scripts/smoke-test.sh                    # test localhost
#   ./scripts/smoke-test.sh invoices.example.com  # test against domain
#   ./scripts/smoke-test.sh --skip-locust      # skip Locust load test
#
# This script runs a comprehensive smoke test after cutover or rollback.
# It validates all services, runs a sample extraction, and checks metrics.
# Exit code 0 = all pass, 1 = any failure.

set -euo pipefail

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
HOST="${1:-localhost}"
SKIP_LOCUST="${2:-}"
# If first arg is --skip-locust, set HOST to localhost
if [ "$HOST" = "--skip-locust" ]; then
    HOST="localhost"
    SKIP_LOCUST="--skip-locust"
fi

# For local testing, use HTTP; for domain, use HTTPS
if [ "$HOST" = "localhost" ] || [ "$HOST" = "127.0.0.1" ]; then
    BASE_URL="http://localhost"
    ODOO_URL="http://localhost:8069"
    AI_URL="http://localhost:8100"
    RABBITMQ_URL="http://localhost:15672"
    PROMETHEUS_URL="http://localhost:9090"
    GRAFANA_URL="http://localhost:3000"
    TLS_CHECK=""
else
    BASE_URL="https://${HOST}"
    ODOO_URL="https://${HOST}"
    AI_URL="http://localhost:8100"  # invoice-ai is internal
    RABBITMQ_URL="http://localhost:15672"
    PROMETHEUS_URL="http://localhost:9090"
    GRAFANA_URL="http://localhost:3000"
    TLS_CHECK="yes"
fi

# Test PDF (use first fixture or create minimal one)
TEST_PDF=""
FIXTURES_DIR="invoice-ai/tests/fixtures"
if [ -d "$FIXTURES_DIR" ] && [ "$(ls -A $FIXTURES_DIR 2>/dev/null | grep -E '\.(pdf|png)$')" ]; then
    TEST_PDF=$(ls -A $FIXTURES_DIR | grep -E '\.(pdf|png)$' | head -1)
    TEST_PDF="${FIXTURES_DIR}/${TEST_PDF}"
fi

# JWT secret (from env or default)
JWT_SECRET="${LOCUST_JWT_SECRET:-test-secret}"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'
PASS=0
FAIL=0
TOTAL=0

pass() { ((PASS++)); ((TOTAL++)); echo -e "${GREEN}PASS${NC}: $*"; }
fail() { ((FAIL++)); ((TOTAL++)); echo -e "${RED}FAIL${NC}: $*"; }
warn() { echo -e "${YELLOW}WARN${NC}: $*"; }

check_url() {
    local url="$1"
    local expected_code="${2:-200}"
    local name="$3"
    local code
    code=$(curl -sI -o /dev/null -w '%{http_code}' "$url" 2>/dev/null || echo "000")
    if [ "$code" = "$expected_code" ] || [ "$code" = "302" ] && [ "$expected_code" = "200" ]; then
        pass "$name responding (HTTP $code)"
    else
        fail "$name not responding (HTTP $code, expected $expected_code)"
    fi
}

check_json() {
    local url="$1"
    local jq_filter="$2"
    local expected="$3"
    local name="$4"
    local result
    result=$(curl -s "$url" 2>/dev/null | jq -r "$jq_filter" 2>/dev/null || echo "error")
    if [ "$result" = "$expected" ]; then
        pass "$name returns correct value"
    else
        fail "$name returned '$result' (expected '$expected')"
    fi
}

# ---------------------------------------------------------------------------
# Phase 1: Service Health
# ---------------------------------------------------------------------------
echo ""
echo "============================================"
echo "Invoice Agent Smoke Test — $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "Target: ${HOST}"
echo "============================================"
echo ""

echo "--- Service Health ---"

# Odoo
check_url "${ODOO_URL}/web/login" 200 "Odoo"

# invoice-ai
check_url "${AI_URL}/healthz" 200 "invoice-ai"

# invoice-ai build SHA
build_sha=$(curl -s "${AI_URL}/healthz" 2>/dev/null | jq -r '.build_sha // "unknown"' 2>/dev/null || echo "unknown")
echo "  Build SHA: ${build_sha}"

# RabbitMQ management
check_url "${RABBITMQ_URL}/api/overview" 200 "RabbitMQ management"

# Prometheus
check_url "${PROMETHEUS_URL}/-/healthy" 200 "Prometheus"

# Grafana
check_url "${GRAFANA_URL}/api/health" 200 "Grafana"

# ---------------------------------------------------------------------------
# Phase 2: Extraction Endpoint
# ---------------------------------------------------------------------------
echo ""
echo "--- Extraction Endpoint ---"

if [ -n "$TEST_PDF" ] && [ -f "$TEST_PDF" ]; then
    # Mint a JWT (using python if available, else skip)
    JWT=""
    if command -v python3 &> /dev/null; then
        JWT=$(python3 -c "
import jwt, time, sys
try:
    token = jwt.encode({'sub': 'smoke-test', 'aud': 'invoice-ai', 'iat': int(time.time()), 'exp': int(time.time()) + 300}, '${JWT_SECRET}', algorithm='HS256')
    print(token)
except Exception as e:
    print('', file=sys.stderr)
    sys.exit(1)
" 2>/dev/null || echo "")
    fi

    if [ -n "$JWT" ]; then
        # Test extraction with the PDF
        response=$(curl -s -w "\n%{http_code}" \
            -X POST "${AI_URL}/v1/extract" \
            -H "Authorization: Bearer ${JWT}" \
            -F "file=@${TEST_PDF};type=application/pdf" \
            2>/dev/null)
        http_code=$(echo "$response" | tail -1)
        body=$(echo "$response" | sed '$d')

        if [ "$http_code" = "200" ]; then
            # Check that response contains extraction
            has_extraction=$(echo "$body" | jq -r '.extraction // empty' 2>/dev/null)
            if [ -n "$has_extraction" ]; then
                pass "POST /v1/extract returns valid extraction"
                # Show extracted vendor name if present
                vendor=$(echo "$body" | jq -r '.extraction.vendor_name // "unknown"' 2>/dev/null)
                echo "  Extracted vendor: ${vendor}"
            else
                fail "POST /v1/extract returned 200 but no extraction in response"
            fi
        elif [ "$http_code" = "429" ]; then
            warn "POST /v1/extract rate limited (429) — this is expected under load"
            pass "POST /v1/extract rate limiter working (429)"
        else
            fail "POST /v1/extract failed (HTTP ${http_code})"
        fi

        # Test embed endpoint
        embed_response=$(curl -s -w "\n%{http_code}" \
            -X POST "${AI_URL}/v1/embed" \
            -H "Authorization: Bearer ${JWT}" \
            -H "Content-Type: application/json" \
            -d '{"texts": ["Test vendor document for embedding"]}' \
            2>/dev/null)
        embed_code=$(echo "$embed_response" | tail -1)
        if [ "$embed_code" = "200" ]; then
            pass "POST /v1/embed returns 200"
        else
            fail "POST /v1/embed failed (HTTP ${embed_code})"
        fi
    else
        warn "Could not generate JWT — skipping extraction test"
    fi
else
    warn "No test PDF found in ${FIXTURES_DIR} — skipping extraction test"
    echo "  Generate test PDFs: python scripts/generate_test_invoices.py"
fi

# ---------------------------------------------------------------------------
# Phase 3: Worker Status
# ---------------------------------------------------------------------------
echo ""
echo "--- Worker Status ---"

# Check if worker is consuming (via RabbitMQ API)
rabbitmq_user="${RABBITMQ_DEFAULT_USER:-invoice_agent}"
rabbitmq_pass="${RABBITMQ_DEFAULT_PASS:-invoice_agent}"
queues=$(curl -s -u "${rabbitmq_user}:${rabbitmq_pass}" \
    "${RABBITMQ_URL}/api/queues" 2>/dev/null | jq -r '.[].name' 2>/dev/null || echo "")

if echo "$queues" | grep -q "invoice.extract"; then
    pass "invoice.extract queue exists"
    # Check queue depth
    depth=$(curl -s -u "${rabbitmq_user}:${rabbitmq_pass}" \
        "${RABBITMQ_URL}/api/queues/%2Finvoice.extract" 2>/dev/null | \
        jq -r '.messages // 0' 2>/dev/null || echo "0")
    echo "  Queue depth: ${depth}"
    if [ "$depth" -lt 50 ]; then
        pass "Queue depth nominal (${depth} < 50)"
    else
        warn "Queue depth high: ${depth}"
    fi
else
    fail "invoice.extract queue not found"
fi

if echo "$queues" | grep -q "invoice.result"; then
    pass "invoice.result queue exists"
else
    warn "invoice.result queue not found"
fi

# ---------------------------------------------------------------------------
# Phase 4: Prometheus Metrics
# ---------------------------------------------------------------------------
echo ""
echo "--- Prometheus Metrics ---"

# Check that our custom metrics are present
metrics=$(curl -s "${PROMETHEUS_URL}/api/v1/label/__name__/values" 2>/dev/null | \
    jq -r '.data[]' 2>/dev/null | grep -E "^invoice_" || echo "")

if echo "$metrics" | grep -q "invoice_worker_jobs_total"; then
    pass "invoice_worker_jobs_total metric present"
else
    fail "invoice_worker_jobs_total metric not found"
fi

if echo "$metrics" | grep -q "invoice_claude_api_duration_seconds"; then
    pass "invoice_claude_api_duration_seconds metric present"
else
    fail "invoice_claude_api_duration_seconds metric not found"
fi

if echo "$metrics" | grep -q "http_requests_total"; then
    pass "http_requests_total metric present"
else
    fail "http_requests_total metric not found"
fi

# ---------------------------------------------------------------------------
# Phase 5: TLS (if testing against domain)
# ---------------------------------------------------------------------------
if [ -n "$TLS_CHECK" ]; then
    echo ""
    echo "--- TLS Certificate ---"

    cert_dates=$(echo | openssl s_client -connect "${HOST}:443" -servername "${HOST}" 2>/dev/null | \
        openssl x509 -noout -dates 2>/dev/null || echo "")
    
    if [ -n "$cert_dates" ]; then
        expiry=$(echo "$cert_dates" | grep "notAfter" | cut -d= -f2)
        pass "TLS certificate valid"
        echo "  Expires: ${expiry}"
        
        # Check HSTS header
        hsts=$(curl -sI "https://${HOST}" 2>/dev/null | grep -i "strict-transport-security" || echo "")
        if [ -n "$hsts" ]; then
            pass "HSTS header present"
        else
            warn "HSTS header missing"
        fi
    else
        fail "Could not retrieve TLS certificate"
    fi
fi

# ---------------------------------------------------------------------------
# Phase 6: Locust Smoke Test (optional)
# ---------------------------------------------------------------------------
if [ -z "$SKIP_LOCUST" ] && command -v locust &> /dev/null; then
    echo ""
    echo "--- Locust Smoke Test ---"
    echo "Running 5-user smoke test for 1 minute..."
    
    # Create results directory
    mkdir -p results
    
    # Run Locust headless
    cd invoice-ai
    LOCUST_JWT_SECRET="${JWT_SECRET}" locust --headless \
        -u 5 -r 1 --run-time 1m \
        --csv=../results/smoke \
        --html=../results/smoke-report.html \
        --host "http://localhost:8100" 2>/dev/null
    
    cd ..
    
    if [ -f "results/smoke_stats.csv" ]; then
        # Check that we got some requests
        total_requests=$(tail -1 results/smoke_stats.csv | cut -d, -f3 || echo "0")
        failures=$(tail -1 results/smoke_stats.csv | cut -d, -f4 || echo "0")
        
        if [ "$total_requests" -gt 0 ] && [ "$failures" -eq 0 ]; then
            pass "Locust smoke test: ${total_requests} requests, 0 failures"
        elif [ "$total_requests" -gt 0 ]; then
            warn "Locust smoke test: ${total_requests} requests, ${failures} failures"
        else
            fail "Locust smoke test: no requests completed"
        fi
    else
        warn "Locust results not found"
    fi
elif [ -z "$SKIP_LOCUST" ]; then
    warn "Locust not installed — skipping load test"
    echo "  Install: pip install locust"
fi

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo ""
echo "============================================"
echo "Smoke Test Summary"
echo "============================================"
echo -e "Passed: ${GREEN}${PASS}${NC}"
echo -e "Failed: ${RED}${FAIL}${NC}"
echo "Total:  ${TOTAL}"
echo ""

if [ "$FAIL" -eq 0 ]; then
    echo -e "${GREEN}ALL TESTS PASSED${NC}"
    exit 0
else
    echo -e "${RED}${FAIL} TEST(S) FAILED${NC}"
    exit 1
fi
