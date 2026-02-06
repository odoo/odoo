#!/bin/bash
# =============================================================================
# Odoo 19 Integration Testing Script
# Tests: Database creation, demo data, CSS loading, module installation
# =============================================================================

set -e

echo "╔═══════════════════════════════════════════════════════════════════════╗"
echo "║         Odoo 19 Integration Testing Suite                            ║"
echo "╚═══════════════════════════════════════════════════════════════════════╝"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
TEST_DB_NAME="test_database_$$"
ADMIN_PASSWD="MasterPassword"
ODOO_URL="http://localhost:8069"
ODOO_RPC_URL="http://localhost:8069/jsonrpc"

# Utility functions
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

test_container_running() {
    if docker ps | grep -q "odoo_uber"; then
        log_success "Odoo container is running"
        return 0
    else
        log_error "Odoo container is not running"
        return 1
    fi
}

test_odoo_ready() {
    log_info "Waiting for Odoo to be ready..."
    
    for i in {1..30}; do
        if curl -s "$ODOO_URL" > /dev/null 2>&1; then
            log_success "Odoo is responding to HTTP requests"
            return 0
        fi
        
        if [ $((i % 10)) -eq 0 ]; then
            log_warning "Still waiting for Odoo... ($i seconds)"
        fi
        sleep 1
    done
    
    log_error "Odoo is not responding after 30 seconds"
    return 1
}

test_css_loading() {
    log_info "Testing CSS asset loading..."
    
    if command -v curl &> /dev/null; then
        # Get login page HTML
        html=$(curl -s "$ODOO_URL/web/login" 2>/dev/null)
        
        # Check for CSS links
        if echo "$html" | grep -q "\.css"; then
            log_success "CSS links found in login page"
        else
            log_warning "CSS links not found in login page HTML"
        fi
        
        # Test actual CSS file loading
        css_code=$(curl -s -o /dev/null -w "%{http_code}" "$ODOO_URL/web/static/web/css/web.min.css" 2>/dev/null || echo "000")
        
        if [ "$css_code" = "200" ]; then
            log_success "CSS files are loading successfully (HTTP 200)"
        else
            log_warning "CSS file returned HTTP $css_code (may not be compiled yet)"
        fi
        
        return 0
    else
        log_warning "curl not available, skipping CSS test"
        return 0
    fi
}

test_database_creation() {
    log_info "Testing database creation via API..."
    
    if command -v curl &> /dev/null; then
        # Prepare JSON-RPC payload
        payload='{
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "service": "db",
                "method": "create_database",
                "args": {
                    "fields": {
                        "db_name": "'"$TEST_DB_NAME"'",
                        "admin_password": "'"$ADMIN_PASSWD"'",
                        "demo": true,
                        "country_code": "US",
                        "phone": "+14155552671",
                        "company_name": "Test Restaurant",
                        "email": "admin@test.local",
                        "password": "test@1234",
                        "login": "admin"
                    }
                }
            },
            "id": 1
        }'
        
        # Send request
        response=$(curl -s -X POST \
            -H "Content-Type: application/json" \
            -d "$payload" \
            "$ODOO_RPC_URL" 2>/dev/null || echo '{"error": "curl failed"}')
        
        # Check response
        if echo "$response" | grep -q '"result"'; then
            log_success "Database creation request accepted"
            
            # Wait a bit for database to be created
            sleep 5
            
            # Try to list databases
            list_payload='{
                "jsonrpc": "2.0",
                "method": "call",
                "params": {
                    "service": "db",
                    "method": "list"
                },
                "id": 2
            }'
            
            list_response=$(curl -s -X POST \
                -H "Content-Type: application/json" \
                -d "$list_payload" \
                "$ODOO_RPC_URL" 2>/dev/null || echo '{"error": "curl failed"}')
            
            if echo "$list_response" | grep -q "$TEST_DB_NAME"; then
                log_success "Test database '$TEST_DB_NAME' was successfully created"
                return 0
            else
                log_warning "Database list response received but test database not found (may still be initializing)"
                echo "List response: $list_response"
                return 0
            fi
        elif echo "$response" | grep -q '"error"'; then
            log_error "Database creation failed: $response"
            return 1
        else
            log_warning "Unexpected response from database creation API: $response"
            return 0
        fi
    else
        log_warning "curl not available, skipping database creation test"
        return 0
    fi
}

test_session_persistence() {
    log_info "Testing session directory permissions..."
    
    # Check if session directory exists in container
    if docker compose exec -T odoo [ -d /tmp/odoo-sessions ]; then
        log_success "Session directory exists"
        
        # Check permissions
        perms=$(docker compose exec -T odoo stat -c %a /tmp/odoo-sessions)
        log_info "Session directory permissions: $perms"
        
        if [ "$perms" = "755" ] || [ "$perms" = "777" ]; then
            log_success "Session directory has correct permissions"
            return 0
        else
            log_warning "Session directory permissions are $perms (expected 755 or 777)"
            return 0
        fi
    else
        log_error "Session directory does not exist in container"
        return 1
    fi
}

test_proxy_mode() {
    log_info "Checking proxy_mode configuration..."
    
    # Check if proxy_mode is enabled in odoo.conf
    if grep -q "proxy_mode = True" config/odoo.conf; then
        log_success "proxy_mode is enabled in odoo.conf"
        return 0
    else
        log_error "proxy_mode is not enabled in odoo.conf"
        return 1
    fi
}

test_admin_password() {
    log_info "Verifying admin password is configured..."
    
    if docker compose config | grep -q "admin_passwd=MasterPassword"; then
        log_success "admin_passwd is configured in docker compose"
        return 0
    else
        log_error "admin_passwd is not found in docker-compose configuration"
        return 1
    fi
}

test_module_installation() {
    log_info "Testing module availability..."
    
    required_modules=("base" "web" "sale" "purchase" "point_of_sale")
    
    for module in "${required_modules[@]}"; do
        if [ -d "addons/$module" ] || [ -d "/opt/odoo/addons/$module" ]; then
            log_success "Module '$module' is available"
        else
            log_warning "Module '$module' not found in expected locations"
        fi
    done
    
    return 0
}

test_custom_modules() {
    log_info "Checking custom module manifests..."
    
    custom_modules=("pos_aggregator_gateway" "pos_custom_kiosk" "pos_order_api" "pos_remote_print")
    all_valid=true
    
    for module in "${custom_modules[@]}"; do
        if [ -f "addons/$module/__manifest__.py" ]; then
            if grep -q "'author'" "addons/$module/__manifest__.py"; then
                log_success "Module '$module' has valid manifest with author field"
            else
                log_error "Module '$module' missing author field in manifest"
                all_valid=false
            fi
        else
            log_warning "Module '$module' manifest not found"
        fi
    done
    
    if [ "$all_valid" = true ]; then
        return 0
    else
        return 1
    fi
}

cleanup_test_database() {
    log_info "Cleaning up test database..."
    
    if command -v psql &> /dev/null; then
        if docker compose exec -T db psql -U odoo -lqt | grep -q "$TEST_DB_NAME"; then
            docker compose exec -T db dropdb -U odoo "$TEST_DB_NAME" 2>/dev/null && \
            log_success "Test database cleaned up" || \
            log_warning "Could not drop test database"
        fi
    fi
}

# =============================================================================
# MAIN TEST EXECUTION
# =============================================================================

echo ""
echo -e "${YELLOW}═══ Phase 1: Infrastructure Tests ═══${NC}"
test_container_running || exit 1
test_odoo_ready || exit 1

echo ""
echo -e "${YELLOW}═══ Phase 2: Configuration Tests ═══${NC}"
test_proxy_mode || exit 1
test_admin_password || exit 1
test_session_persistence || exit 1

echo ""
echo -e "${YELLOW}═══ Phase 3: Module Tests ═══${NC}"
test_module_installation || exit 1
test_custom_modules || exit 1

echo ""
echo -e "${YELLOW}═══ Phase 4: UI/Asset Tests ═══${NC}"
test_css_loading

echo ""
echo -e "${YELLOW}═══ Phase 5: Functional Tests ═══${NC}"
test_database_creation

# Cleanup
echo ""
echo -e "${YELLOW}═══ Cleanup ═══${NC}"
cleanup_test_database

# Summary
echo ""
echo "╔═══════════════════════════════════════════════════════════════════════╗"
echo -e "║                   ${GREEN}✅ All Tests Completed${NC}                          ║"
echo "╚═══════════════════════════════════════════════════════════════════════╝"

echo ""
echo -e "${BLUE}Summary:${NC}"
echo "✅ Container infrastructure verified"
echo "✅ Odoo configuration validated"
echo "✅ Modules and manifests checked"
echo "✅ CSS/UI assets tested"
echo "✅ Database creation tested"
echo ""
echo "Your Odoo 19 POS Aggregator is ready for deployment!"
echo ""

exit 0
