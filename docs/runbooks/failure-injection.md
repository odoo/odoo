# Runbook: Failure Injection Testing — v0.11 Production Readiness

**Purpose**: Validate that the system survives infrastructure failures by
deliberately breaking components and measuring recovery time.

**When**: During the v0.11 milestone, after the full stack is deployed and
monitoring is confirmed working.

---

## Prerequisites

- Prometheus/Grafana stack running and all targets UP
- Pipeline error rate at 0%
- Queue depth at 0
- S3 backups bucket has at least one recent pg_dump

## Test 1: Kill the Worker Container

**Simulates**: Worker process crash mid-extraction

```bash
docker compose kill worker
```

**What should happen**:
- RabbitMQ marks unacked messages as "unacked" → redelivers on restart
- Alerts fire: WorkerQueueBacklog (queue depth rises)
- Worker auto-restarts (restart: unless-stopped)
- Messages are redelivered, no invoices lost

**Measure**:
- Time from kill to worker healthy again: ~10-30s (Docker restart policy)
- Time for queue to drain to 0: depends on backlog

**Verify**:
```bash
docker compose ps worker  # Should show "Up" within 30s
docker compose exec rabbitmq rabbitmqctl list_queues name messages consumers
```

## Test 2: Reboot the EC2 Instance

**Simulates**: Kernel panic, power loss, or maintenance window

```bash
# From your local machine (requires AWS CLI configured)
aws ec2 reboot-instances --instance-ids <instance-id>
```

**What should happen**:
- All containers stop immediately
- RDS survives (separate infrastructure, Multi-AZ)
- ElastiCache survives (separate infrastructure)
- S3 survives (managed service)
- On boot: cloud-init runs docker-compose up → all services restart
- Sessions in Redis are NOT lost (ElastiCache is external)
- LLM cache in Redis is NOT lost

**Measure**:
- Time from reboot command to SSH available: ~60-90s
- Time from SSH to docker-compose up: ~30-60s
- Time from containers running to healthcheck passing: ~10-30s
- Total RTO: ~2-3 minutes

**Verify**:
```bash
# SSH into the instance after reboot
docker compose ps  # All services should be "Up"
docker compose logs --tail=20 worker
# Check Prometheus: all targets should return to UP
```

## Test 3: Force RDS Failover

**Simulates**: AZ failure requiring automatic failover to standby

```bash
aws rds reboot-db-instance \
  --db-instance-identifier odoo-invoice-agent-production-db \
  --force-failover
```

**What should happen**:
- Brief connection interruption (30-60 seconds)
- All services see "connection refused" temporarily
- RDS promotes the standby to primary
- Connections automatically reconnect
- No data loss (synchronous replication)

**Measure**:
- Time from command to first connection error: ~0-10s
- Time of connection unavailability: ~30-90s
- Time to full recovery: ~1-2 minutes

**Verify**:
```bash
# After recovery, check connections are re-established
psql -h <new-rds-endpoint> -U odoo_user -d odoo -c "SELECT 1;"
# Check Grafana: PostgreSQL connections panel should show recovery
```

## Test 4: Break the Claude API Key (Alert Fire Test)

**Simulates**: API key rotation failure, billing issue

```bash
# Set an invalid API key
export ANTHROPIC_API_KEY="sk-ant-invalid-key-for-testing"

# Restart the worker with the broken key
docker compose restart worker
```

**What should happen**:
- First invoice extraction fails with ClaudeRateLimitError or auth error
- Error rate spikes above 2%
- PipelineErrorRateHigh alert fires after 5 minutes
- Alertmanager routes to Slack/email
- Queue depth rises as messages retry through the ladder

**Measure**:
- Time from bad key to first error: immediate
- Time from error spike to alert firing: ~5 minutes (for duration)
- Time from alert to Slack notification: ~10-30 seconds

**Revert**:
```bash
# Restore the real API key
export ANTHROPIC_API_KEY="<real-key>"
docker compose restart worker

# Watch the alert resolve
# Alertmanager sends "resolved" notification
```

**Verify**:
- Slack/email receives the alert
- After revert, Slack/email receives "resolved" notification
- Error rate drops to 0%
- Queue drains to 0

## Test 5: Fill the Disk (NodeDiskSpaceLow)

**Simulates**: Log accumulation filling the disk

```bash
# Create a 50GB file (assuming ~80GB disk)
fallocate -l 50G /tmp/fill-disk
# Wait for alert to fire
# Then clean up
rm /tmp/fill-disk
```

**What should happen**:
- Disk free drops below 10%
- NodeDiskSpaceLow alert fires after 5 minutes
- System continues operating (reads from cache/RDS are unaffected)

## Recording Results

After each test, record in this table:

| Test | Start Time | Recovery Time | Data Loss | Alert Fired | Alert Resolved |
|------|------------|---------------|-----------|-------------|----------------|
| Worker kill | | | | | |
| EC2 reboot | | | | | |
| RDS failover | | | | | |
| API key break | | | | | |
| Disk fill | | | | | |

## Post-Test Cleanup

1. Verify all alerts are in "resolved" state
2. Confirm queue depth is 0
3. Upload a test invoice to verify end-to-end functionality
4. Update this runbook with actual measured times
