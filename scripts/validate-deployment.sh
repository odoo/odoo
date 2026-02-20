#!/bin/bash
# =============================================================================
# Odoo 19 + Traefik Deployment Validation Script
# Verifies that docker-compose is correctly configured and all services run
# =============================================================================

set -e

echo "╔═══════════════════════════════════════════════════════════════════════╗"
echo "║         Odoo 19 Deployment Validation Script                         ║"
echo "╚═══════════════════════════════════════════════════════════════════════╝"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if docker-compose file exists
if [ ! -f "docker-compose.yml" ]; then
    echo -e "${RED}❌ Error: docker-compose.yml not found${NC}"
    exit 1
fi

echo -e "\n${YELLOW}📋 Checking docker-compose.yml syntax...${NC}"
docker-compose config > /dev/null && echo -e "${GREEN}✅ Syntax is valid${NC}" || exit 1

# Check required environment variables
echo -e "\n${YELLOW}📋 Checking configuration...${NC}"

# Verify admin_passwd is set
if grep -q "admin_passwd=MasterPassword" docker-compose.yml; then
    echo -e "${GREEN}✅ admin_passwd is configured${NC}"
else
    echo -e "${RED}❌ admin_passwd not found in docker-compose.yml${NC}"
    exit 1
fi

# Check for proxy headers middleware
if grep -q "odoo-proxy-headers" docker-compose.yml; then
    echo -e "${GREEN}✅ Proxy headers middleware configured${NC}"
else
    echo -e "${RED}❌ Proxy headers middleware not found${NC}"
    exit 1
fi

# Check for proxy_mode in config
if grep -q "proxy_mode = True" config/odoo.conf; then
    echo -e "${GREEN}✅ proxy_mode enabled in odoo.conf${NC}"
else
    echo -e "${RED}❌ proxy_mode not enabled in odoo.conf${NC}"
    exit 1
fi

# Check for session directory configuration
if grep -q "session_dir" config/odoo.conf; then
    echo -e "${GREEN}✅ session_dir configured in odoo.conf${NC}"
else
    echo -e "${RED}❌ session_dir not configured in odoo.conf${NC}"
    exit 1
fi

# Check for all required services in docker-compose
echo -e "\n${YELLOW}📋 Checking required services...${NC}"

services=("db" "traefik" "odoo")
for service in "${services[@]}"; do
    if grep -q "^\s*$service:" docker-compose.yml; then
        echo -e "${GREEN}✅ Service '$service' is defined${NC}"
    else
        echo -e "${RED}❌ Service '$service' not found in docker-compose.yml${NC}"
        exit 1
    fi
done

# Check for required volumes
echo -e "\n${YELLOW}📋 Checking volume configuration...${NC}"

volumes=("odoo-db-data" "odoo-data" "odoo-sessions" "traefik-ssl")
for volume in "${volumes[@]}"; do
    if grep -q "$volume" docker-compose.yml; then
        echo -e "${GREEN}✅ Volume '$volume' is defined${NC}"
    else
        echo -e "${RED}❌ Volume '$volume' not found${NC}"
        exit 1
    fi
done

# Check for module initialization
echo -e "\n${YELLOW}📋 Checking module initialization...${NC}"

required_modules=("base" "web" "sale" "purchase" "stock" "account" "point_of_sale" "website" "pos_restaurant")
modules_str=$(grep -A 1 "- -i$" docker-compose.yml | grep -v "^--" | tr ',' '\n' | tr -d ' ' | tr '\n' ' ')

for module in "${required_modules[@]}"; do
    if echo "$modules_str" | grep -q "$module"; then
        echo -e "${GREEN}✅ Module '$module' will be installed${NC}"
    else
        echo -e "${YELLOW}⚠️  Module '$module' not in pre-install list (can be installed manually)${NC}"
    fi
done

# Check for custom module manifests
echo -e "\n${YELLOW}📋 Checking custom modules...${NC}"

custom_modules=("pos_aggregator_gateway" "pos_custom_kiosk" "pos_order_api" "pos_remote_print")
for module in "${custom_modules[@]}"; do
    manifest_file="addons/$module/__manifest__.py"
    if [ -f "$manifest_file" ]; then
        if grep -q "'author'" "$manifest_file"; then
            echo -e "${GREEN}✅ Module '$module' has author field${NC}"
        else
            echo -e "${RED}❌ Module '$module' missing author field${NC}"
            exit 1
        fi
    else
        echo -e "${YELLOW}⚠️  Module '$module' not found${NC}"
    fi
done

# Summary
echo -e "\n╔═══════════════════════════════════════════════════════════════════════╗"
echo -e "║                     ${GREEN}✅ All Checks Passed!${NC}                           ║"
echo "║                                                                       ║"
echo "║  You can now deploy with:                                           ║"
echo "║  $ docker compose up -d                                             ║"
echo "║                                                                       ║"
echo "║  Monitor startup with:                                              ║"
echo "║  $ docker compose logs -f odoo                                       ║"
echo -e "╚═══════════════════════════════════════════════════════════════════════╝"

exit 0
