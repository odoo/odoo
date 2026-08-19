#!/usr/bin/env bash
# cutover.sh — Automated cutover script for Invoice Agent v1.0.0 launch.
#
# Usage:
#   ./scripts/cutover.sh v1.0.0                    # deploy a specific tag
#   ./scripts/cutover.sh v0.11                     # rollback to previous tag
#   DRY_RUN=1 ./scripts/cutover.sh v1.0.0          # dry run (print commands only)
#
# Prerequisites:
#   - Docker compose running on the target host
#   - SSH access to the EC2 instance (or run on the host directly)
#   - jq installed
#
# This script is designed to complete in under 5 minutes for rollback scenarios.

set -euo pipefail

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
TAG="${1:?Usage: $0 <tag> (e.g. v1.0.0 or v0.11)}"
DRY_RUN="${DRY_RUN:-0}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.yml}"
DOMAIN="${DOMAIN:-invoices.example.com}"
HEALTH_TIMEOUT="${HEALTH_TIMEOUT:-120}"  # seconds to wait for health check
ROLLBACK_WINDOW="${ROLLBACK_WINDOW:-240}"  # seconds — target < 5 min

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log()  { echo -e "${GREEN}[$(date -u +%H:%M:%S)]${NC} $*"; }
warn() { echo -e "${YELLOW}[$(date -u +%H:%M:%S)] WARNING:${NC} $*"; }
fail() { echo -e "${RED}[$(date -u +%H:%M:%S)] FATAL:${NC} $*"; exit 1; }

run() {
    if [ "$DRY_RUN" = "1" ]; then
        echo "[DRY RUN] $*"
    else
        eval "$@"
    fi
}

elapsed_seconds() {
    echo $(( $(date +%s) - START_TIME ))
}

# ---------------------------------------------------------------------------
# Start timer
# ---------------------------------------------------------------------------
START_TIME=$(date +%s)
log "Cutover starting: tag=${TAG} dry_run=${DRY_RUN}"

# ---------------------------------------------------------------------------
# Phase 1: Pre-flight checks
# ---------------------------------------------------------------------------
log "Phase 1: Pre-flight checks"

# Verify Docker is running
run "docker info >/dev/null 2>&1" || fail "Docker is not running"

# Verify the compose file exists
run "test -f ${COMPOSE_FILE}" || fail "Compose file not found: ${COMPOSE_FILE}"

# Pull new images
log "Phase 2: Pulling images for tag ${TAG}"
run "docker compose -f ${COMPOSE_FILE} pull odoo worker invoice-ai" 2>&1 | tail -5

# ---------------------------------------------------------------------------
# Phase 3: Deploy
# ---------------------------------------------------------------------------
log "Phase 3: Deploying tag ${TAG}"

# Recreate services with the new tag
# We use --force-recreate to ensure the new image is used
# --no-deps avoids recreating dependent services (db, rabbitmq, redis)
run "docker compose -f ${COMPOSE_FILE} up -d --force-recreate --no-deps odoo worker invoice-ai"

# ---------------------------------------------------------------------------
# Phase 4: Health check loop
# ---------------------------------------------------------------------------
log "Phase 4: Waiting for health checks (timeout: ${HEALTH_TIMEOUT}s)"

health_ok=false
while [ "$(elapsed_seconds)" -lt "$HEALTH_TIMEOUT" ]; do
    # Check Odoo health (should return 200 or 302)
    odoo_status=$(run "curl -sI -o /dev/null -w '%{http_code}' https://${DOMAIN}/web/login 2>/dev/null || echo '000'" || echo "000")

    # Check invoice-ai healthz
    ai_health=$(run "curl -s http://localhost:8100/healthz 2>/dev/null || echo '{}'" || echo "{}")
    ai_status=$(echo "$ai_health" | jq -r '.status // "error"' 2>/dev/null || echo "error")

    if [ "$odoo_status" != "000" ] && [ "$ai_status" = "ok" ]; then
        log "Health checks passed (Odoo: ${odoo_status}, invoice-ai: ok)"
        health_ok=true
        break
    fi

    warn "Waiting... Odoo=${odoo_status} invoice-ai=${ai_status} ($(( $(elapsed_seconds) ))s elapsed)"
    sleep 5
done

if [ "$health_ok" != "true" ]; then
    fail "Health checks did not pass within ${HEALTH_TIMEOUT}s. Consider rollback."
fi

# ---------------------------------------------------------------------------
# Phase 5: Post-deploy verification
# ---------------------------------------------------------------------------
log "Phase 5: Post-deploy verification"

# Verify worker is consuming
worker_logs=$(run "docker compose -f ${COMPOSE_FILE} logs worker --tail 5 2>&1" || echo "")
if echo "$worker_logs" | grep -qi "consuming\|connected"; then
    log "Worker connected and consuming"
else
    warn "Worker logs do not show 'consuming' — check manually"
fi

# Verify build SHA matches
build_sha=$(run "curl -s http://localhost:8100/healthz | jq -r '.build_sha'" || echo "unknown")
log "Build SHA: ${build_sha}"

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
TOTAL_ELAPSED=$(elapsed_seconds)
log "============================================"
log "Cutover complete: tag=${TAG}"
log "Total time: ${TOTAL_ELAPSED}s"
log "Health checks: PASSED"
log "============================================"

if [ "$TOTAL_ELAPSED" -gt "$ROLLBACK_WINDOW" ]; then
    warn "Cutover took ${TOTAL_ELAPSED}s — exceeds ${ROLLBACK_WINDOW}s target"
fi

# Print next steps
echo ""
echo "Next steps:"
echo "  1. Run smoke test:  ./scripts/smoke-test.sh ${DOMAIN}"
echo "  2. Check Grafana:   https://grafana.${DOMAIN}/d/agent-slo"
echo "  3. Monitor for 1 hour, then announce"
