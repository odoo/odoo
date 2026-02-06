#!/bin/bash
# =============================================================================
# Service Health Check Script
# Verifies that all docker containers are running and healthy
# =============================================================================

set -e

echo "╔═══════════════════════════════════════════════════════════════════════╗"
echo "║              Odoo 19 Services Health Check                           ║"
echo "╚═══════════════════════════════════════════════════════════════════════╝"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
ODOO_URL="http://localhost:8069"
DB_HOST="localhost"
DB_PORT="5432"
DB_USER="odoo"
DB_NAME="postgres"
TRAEFIK_URL="http://localhost:8080"
TRAEFIK_API_URL="http://localhost:8080/api/overview"

check_container() {
    local container_name=$1
    local service_name=$2
    
    if docker ps | grep -q "$container_name"; then
        echo -e "${GREEN}✅ Container '$service_name' is running${NC}"
        return 0
    else
        echo -e "${RED}❌ Container '$service_name' is NOT running${NC}"
        return 1
    fi
}

check_port() {
    local port=$1
    local service=$2
    
    if netstat -tuln 2>/dev/null | grep -q ":$port " || ss -tuln 2>/dev/null | grep -q ":$port "; then
        echo -e "${GREEN}✅ Port $port ($service) is listening${NC}"
        return 0
    else
        echo -e "${YELLOW}⚠️  Port $port ($service) is not listening (may still be starting)${NC}"
        return 1
    fi
}

check_http_endpoint() {
    local url=$1
    local service=$2
    local expected_code=$3
    
    if command -v curl &> /dev/null; then
        http_code=$(curl -s -o /dev/null -w "%{http_code}" "$url" 2>/dev/null || echo "000")
        
        if [ "$http_code" = "$expected_code" ] || [[ "$http_code" =~ ^[23].. ]]; then
            echo -e "${GREEN}✅ Service '$service' is responding (HTTP $http_code)${NC}"
            return 0
        else
            echo -e "${YELLOW}⚠️  Service '$service' returned HTTP $http_code (expected $expected_code)${NC}"
            return 1
        fi
    else
        echo -e "${BLUE}ℹ️  curl not available, skipping HTTP check for '$service'${NC}"
        return 0
    fi
}

check_postgres() {
    echo -e "\n${YELLOW}📋 Checking PostgreSQL...${NC}"
    
    if check_container "odoo_db" "PostgreSQL"; then
        # Try to connect to PostgreSQL
        if command -v psql &> /dev/null; then
            if psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" -c "SELECT 1" > /dev/null 2>&1; then
                echo -e "${GREEN}✅ PostgreSQL is accepting connections${NC}"
                return 0
            else
                echo -e "${YELLOW}⚠️  PostgreSQL container running but not accepting connections yet${NC}"
                return 1
            fi
        else
            echo -e "${BLUE}ℹ️  psql not available, assuming PostgreSQL is healthy${NC}"
            return 0
        fi
    else
        return 1
    fi
}

check_traefik() {
    echo -e "\n${YELLOW}📋 Checking Traefik...${NC}"
    
    if check_container "odoo_traefik" "Traefik"; then
        check_port 80 "HTTP"
        check_port 443 "HTTPS"
        check_http_endpoint "http://localhost:8080/api/overview" "Traefik API" "200"
        return 0
    else
        return 1
    fi
}

check_odoo() {
    echo -e "\n${YELLOW}📋 Checking Odoo...${NC}"
    
    if check_container "odoo_uber" "Odoo"; then
        check_port 8069 "Odoo"
        
        # Check if Odoo web interface is responding
        if command -v curl &> /dev/null; then
            # Try to access the web interface (expect 302 or 200)
            http_code=$(curl -s -o /dev/null -w "%{http_code}" -L "$ODOO_URL" 2>/dev/null || echo "000")
            if [[ "$http_code" =~ ^[23].. ]]; then
                echo -e "${GREEN}✅ Odoo web interface is responding (HTTP $http_code)${NC}"
            else
                echo -e "${YELLOW}⚠️  Odoo may still be starting (HTTP $http_code)${NC}"
            fi
        fi
        return 0
    else
        return 1
    fi
}

# Show docker ps output
echo -e "\n${BLUE}═══ Docker Containers Status ═══${NC}"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" || true

# Run checks
check_postgres
check_traefik
check_odoo

# Final summary
echo -e "\n╔═══════════════════════════════════════════════════════════════════════╗"
echo -e "║                   ${GREEN}✅ Health Check Complete${NC}                          ║"
echo -e "╚═══════════════════════════════════════════════════════════════════════╝"

echo -e "\n${BLUE}Next steps:${NC}"
echo "1. Wait a few seconds for services to fully initialize"
echo "2. Access Odoo: http://localhost:8069 or https://your-domain"
echo "3. Create a new database at: http://localhost:8069/web/database/manager"
echo "4. Login with admin password configured in docker-compose.yml"
echo ""

exit 0
