#!/bin/bash
# RAM Restaurant - Master Test Orchestrator

echo "Starting RAM Restaurant Test Suite..."

# 1. Website Smoke Test
echo "Running Website Smoke Test..."
python3 scripts/test_website.py

# 2. Public Access Verification
echo "Verifying Public Access (ACLs)..."
python3 scripts/verify_public.py

# 3. Remote Order Sync (Simulated)
echo "Testing Remote Order Sync..."
python3 scripts/test_remote_order.py

# 4. Webhook Payload Verification
echo "Testing Webhook HMAC/Payload..."
python3 scripts/webhook_test.py

echo "Tests Complete. Check logs if any failures occurred."
