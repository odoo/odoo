#!/usr/bin/env bash
# =============================================================================
# EC2 Bootstrap — Install Docker Engine + Compose Plugin on Ubuntu 24.04
#
# Usage:
#   ssh ubuntu@<elastic-ip>
#   sudo bash scripts/ec2-bootstrap.sh
#
# What it does:
#   1. Installs Docker Engine via get.docker.com (official script)
#   2. Adds ubuntu user to docker group (no sudo needed)
#   3. Enables Docker on boot
#   4. Verifies docker compose v2 plugin
#   5. Adds swapfile if total memory < 4 GiB
# =============================================================================
set -euo pipefail

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }

# ----------------------------------------------------------------------------
# 1. Install Docker Engine via official convenience script
# ----------------------------------------------------------------------------
if ! command -v docker &>/dev/null; then
    log "Installing Docker Engine..."
    curl -fsSL https://get.docker.com | sh
    log "Docker Engine installed."
else
    log "Docker Engine already installed ($(docker --version))."
fi

# ----------------------------------------------------------------------------
# 2. Add ubuntu user to docker group (no password for docker commands)
# ----------------------------------------------------------------------------
if groups ubuntu | grep -q docker; then
    log "ubuntu user already in docker group."
else
    log "Adding ubuntu to docker group..."
    sudo usermod -aG docker ubuntu
    log "Added. (Log out and back in for group change to take effect.)"
fi

# ----------------------------------------------------------------------------
# 3. Enable Docker on boot
# ----------------------------------------------------------------------------
sudo systemctl enable --now docker
log "Docker service enabled and started."

# ----------------------------------------------------------------------------
# 4. Verify docker compose v2 plugin
# ----------------------------------------------------------------------------
if docker compose version &>/dev/null; then
    log "docker compose plugin: $(docker compose version)"
else
    log "ERROR: docker compose v2 plugin not found. Install it via:"
    log "  sudo apt-get install -y docker-compose-plugin"
    exit 1
fi

# ----------------------------------------------------------------------------
# 5. Add swapfile if memory is tight (< 4 GiB)
# ----------------------------------------------------------------------------
total_mem_kb=$(grep MemTotal /proc/meminfo | awk '{print $2}')
total_mem_gib=$(echo "scale=2; $total_mem_kb / 1024 / 1024" | bc)
log "Total memory: ${total_mem_gib} GiB"

if (( $(echo "$total_mem_gib < 3.5" | bc -l) )); then
    if swapon --show | grep -q /swapfile; then
        log "Swap already active."
    else
        log "Memory < 4 GiB. Creating 2 GiB swapfile..."
        sudo fallocate -l 2G /swapfile
        sudo chmod 600 /swapfile
        sudo mkswap /swapfile
        sudo swapon /swapfile
        echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
        log "Swapfile created and enabled."
    fi
else
    log "Sufficient memory. No swapfile needed."
fi

# ----------------------------------------------------------------------------
# 6. Summary
# ----------------------------------------------------------------------------
echo ""
log "=== Bootstrap Complete ==="
echo "  Docker:       $(docker --version 2>/dev/null || echo 'not found')"
echo "  Compose:      $(docker compose version 2>/dev/null || echo 'not found')"
echo ""
log "NEXT STEPS (run after re-login for docker group):"
echo "  1. Clone the repo: git clone <repo> /opt/invoice-agent"
echo "  2. cd /opt/invoice-agent"
echo "  3. cp .env.example .env && vi .env   # set secrets"
echo "  4. docker compose up -d"
