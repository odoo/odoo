#!/usr/bin/env bash
# =============================================================================
# KSW Odoo — Production Deploy Script
# Usage: ./deploy.sh
#
# FIRST-TIME MIGRATION (systemd → Docker) — run these once before deploying:
#
#   1. Set a PostgreSQL password for the odoo user:
#        sudo -u postgres psql -c "ALTER USER odoo WITH PASSWORD 'your_password';"
#
#   2. Update .env.prod with that password:
#        nano .env.prod   →   set ODOO_DB_PASSWORD=your_password
#
#   3. Stop and disable the systemd service:
#        sudo systemctl stop odoo
#        sudo systemctl disable odoo
#
# After those three steps, run this script to deploy.
# =============================================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
COMPOSE_FILE="$SCRIPT_DIR/docker-compose.prod.yml"
IMAGE="ghcr.io/mohammedj-sadiq/kswco-odoo:latest"

# ── Guard: systemd must be stopped before Docker takes port 8069 ──────────────
if systemctl is-active --quiet odoo 2>/dev/null; then
    echo ""
    echo "ERROR: systemd odoo service is still running on port 8069."
    echo "       Complete the first-time migration steps at the top of this script,"
    echo "       then run again."
    echo ""
    exit 1
fi

# ── Guard: .env.prod password must be filled in ───────────────────────────────
if grep -q "ODOO_DB_PASSWORD=CHANGE_ME" "$SCRIPT_DIR/.env.prod" 2>/dev/null; then
    echo ""
    echo "ERROR: .env.prod still has ODOO_DB_PASSWORD=CHANGE_ME."
    echo "       Set the real password first (see steps at the top of this script)."
    echo ""
    exit 1
fi

echo ""
echo "=== KSW Odoo — Deploy to Production ==="
echo ""

# ── Step 1: Build image with latest committed code ────────────────────────────
echo "→ [1/3] Building image from committed code..."
docker build -t "$IMAGE" "$SCRIPT_DIR"
echo "    ✓ Image built"

# ── Step 2: Replace the running container ─────────────────────────────────────
echo "→ [2/3] Restarting prod container..."
docker compose -f "$COMPOSE_FILE" up -d --remove-orphans
echo "    ✓ Container started"

# ── Step 3: Verify it came up ─────────────────────────────────────────────────
echo "→ [3/3] Waiting for Odoo to respond..."
for i in $(seq 1 30); do
    if curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8069/web/health 2>/dev/null | grep -q "200"; then
        echo "    ✓ Odoo is up (http://127.0.0.1:8069)"
        break
    fi
    sleep 2
    if [ "$i" -eq 30 ]; then
        echo "    ✗ Odoo did not respond in 60s — check logs:"
        echo "      docker compose -f docker-compose.prod.yml logs -f"
        exit 1
    fi
done

echo ""
echo "=== Deploy complete — alkawthersw.ddns.net is live ==="
echo ""
echo "Useful commands:"
echo "  Logs:    docker compose -f docker-compose.prod.yml logs -f"
echo "  Status:  docker compose -f docker-compose.prod.yml ps"
echo "  Restart: docker compose -f docker-compose.prod.yml restart"
echo ""
