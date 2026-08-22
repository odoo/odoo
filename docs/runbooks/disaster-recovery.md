# Disaster Recovery Runbook

> **Last tested:** (fill in after game day)
> **Owner:** (fill in)
> **Review cadence:** Quarterly

---

## Prerequisites

- AWS CLI configured with EC2 instance profile (or IAM user with RDS/S3 access)
- Terraform >= 1.9 installed on the recovery host
- Docker Compose v2 installed
- `.env` file with production secrets (or Secrets Manager access)
- SSH access to EC2 or SSM Session Manager

---

## Decision Tree

```
Incident?
├── RDS unreachable / failed
│   ├── Multi-AZ failover happened automatically? → Check app health, done
│   └── Manual intervention needed? → Go to Scenario A
├── EC2 instance dead
│   └── Go to Scenario B
├── Data deleted accidentally
│   └── Go to Scenario C
└── Bad deploy (app broken after update)
    └── Go to Scenario D
```

---

## Scenario A: RDS Loss / Corruption

**Target RTO:** < 10 minutes (Multi-AZ auto-failover) or < 15 minutes (manual PITR)

### 1. Check if Multi-AZ failover resolved it

```bash
aws rds describe-db-instances \
  --db-instance-identifier invoice-agent-prod \
  --query 'DBInstances[0].DBInstanceStatus' --output text
```

- If `available` → the standby took over. Verify app health: `curl -sf https://domain/web/health`
- If `failed` or `unavailable` → proceed to manual PITR below

### 2. Manual Point-in-Time Restore

```bash
# Restore to a specific timestamp (e.g., 5 minutes before the incident)
RESTORE_TIME="2026-08-19T08:55:00Z"

aws rds restore-db-instance-to-point-in-time \
  --source-db-instance-identifier invoice-agent-prod \
  --target-db-instance-identifier invoice-agent-restore \
  --restore-time "$RESTORE_TIME" \
  --db-instance-class db.t4g.medium \
  --no-publicly-accessible

# Wait for it to become available (typically 5-10 minutes)
aws rds wait db-instance-available \
  --db-instance-identifier invoice-agent-restore
```

### 3. Validate restored data

```bash
RESTORE_ENDPOINT=$(aws rds describe-db-instances \
  --db-instance-identifier invoice-agent-restore \
  --query 'DBInstances[0].Endpoint.Address' --output text)

psql -h "$RESTORE_ENDPOINT" -U odoo_user -d invoice_agent -c \
  "SELECT count(*) FROM account_move WHERE move_type = 'in_invoice';"

psql -h "$RESTORE_ENDPOINT" -U odoo_user -d invoice_agent -c \
  "SELECT id, name, invoice_date, amount_total FROM account_move ORDER BY id DESC LIMIT 10;"
```

### 4. Switch app to the restored instance

```bash
# Update .env on EC2
echo "ODOO_DB_HOST=$RESTORE_ENDPOINT" >> /opt/odoo/.env

# Restart Odoo
cd /opt/odoo && docker compose restart odoo
```

### 5. Cleanup (after validation)

```bash
aws rds delete-db-instance \
  --db-instance-identifier invoice-agent-restore \
  --skip-final-snapshot
```

---

## Scenario B: EC2 Loss (Full Rebuild)

**Target RTO:** < 30 minutes

### 1. Terraform — provision infrastructure (~5 min)

```bash
cd infra/terraform
terraform apply -auto-approve
cd ../..
```

### 2. Get RDS endpoint from Terraform output

```bash
RDS_HOST=$(cd infra/terraform && terraform output -raw rds_endpoint)
REDIS_HOST=$(cd infra/terraform && terraform output -raw redis_endpoint)
S3_BACKUP_BUCKET=$(cd infra/terraform && terraform output -raw backups_bucket)
S3_ATTACHMENT_BUCKET=$(cd infra/terraform && terraform output -raw attachments_bucket)

echo "RDS: $RDS_HOST"
echo "Redis: $REDIS_HOST"
echo "Backup bucket: $S3_BACKUP_BUCKET"
```

### 3. Download latest backup from S3 (~1 min)

```bash
LATEST_BACKUP=$(aws s3 ls "s3://${S3_BACKUP_BUCKET}/daily/" --recursive | \
  grep '\.dump$' | sort | tail -1 | awk '{print $4}')

echo "Latest backup: $LATEST_BACKUP"
aws s3 cp "s3://${S3_BACKUP_BUCKET}/${LATEST_BACKUP}" /tmp/latest.dump
echo "Downloaded: $(du -h /tmp/latest.dump | cut -f1)"
```

### 4. Restore database (~8 min)

```bash
# Get password from Secrets Manager
ODOO_DB_PASSWORD=$(aws secretsmanager get-secret-value \
  --secret-id invoice-agent/odoo-db-password \
  --query 'SecretString' --output text)

PGPASSWORD="$ODOO_DB_PASSWORD" pg_restore \
  -h "$RDS_HOST" -U odoo_user -d invoice_agent \
  --no-owner --no-privileges --clean --if-exists \
  /tmp/latest.dump

echo "Database restored"
```

### 5. Sync filestore from S3 (~3 min)

```bash
mkdir -p /opt/odoo/filestore/invoice_agent

aws s3 sync "s3://${S3_ATTACHMENT_BUCKET}/filestore/invoice_agent/" \
  /opt/odoo/filestore/invoice_agent/ --size-only

echo "Filestore synced"
```

### 6. Update environment variables

```bash
# Update .env with RDS endpoint and secrets
cat > /opt/odoo/.env << EOF
ODOO_DB_HOST=$RDS_HOST
ODOO_DB_PORT=5432
ODOO_DB_USER=odoo_user
ODOO_DB_PASSWORD=$ODOO_DB_PASSWORD
ANTHROPIC_API_KEY=$(aws secretsmanager get-secret-value --secret-id invoice-agent/anthropic-api-key --query 'SecretString' --output text)
INVOICE_AI_JWT_SECRET=$(aws secretsmanager get-secret-value --secret-id invoice-agent/jwt-secret --query 'SecretString' --output text)
REDIS_URL=redis://:${REDIS_AUTH_TOKEN}@${REDIS_HOST}:6379/0
DOMAIN=yourdomain.com
URL=https://yourdomain.com
EOF
```

### 7. Deploy compose stack (~5 min)

```bash
cd /opt/odoo
git clone https://github.com/7ananSaif/odoo.git .
git checkout main

docker compose -f docker-compose.yml \
  -f docker-compose.prod.yml \
  -f docker-compose.prod.rds.yml \
  up -d --build
```

### 8. Wait for health check

```bash
for i in $(seq 1 30); do
  if curl -sf http://localhost:8069/web/health > /dev/null 2>&1; then
    echo "Odoo is healthy after ${i}0 seconds"
    break
  fi
  echo "Waiting... ($i/30)"
  sleep 10
done
```

### 9. Verify end-to-end

```bash
# Check that invoice-ai is reachable
curl -sf http://localhost:8100/healthz

# Check that RabbitMQ is running
docker compose exec rabbitmq rabbitmq-diagnostics -q ping
```

---

## Scenario C: Accidental Data Deletion

**Target RTO:** < 15 minutes

### 1. Identify the deletion time

Check application logs:
```bash
# On EC2
docker compose logs odoo --since "1h" | grep -i "delete\|unlink"
```

Check Odoo's mail.message (audit trail) for the last move_id that was deleted:
```bash
psql -h "$RDS_HOST" -U odoo_user -d invoice_agent -c \
  "SELECT create_date, subject, body FROM mail_message 
   WHERE model='account.move' ORDER BY id DESC LIMIT 10;"
```

### 2. Restore to a scratch instance (Scenario A, step 2)

Restore to a timestamp BEFORE the deletion.

### 3. Validate the data is back

```bash
# On the scratch instance, verify the deleted records exist
psql -h "$RESTORE_ENDPOINT" -U odoo_user -d invoice_agent -c \
  "SELECT id, name, state FROM account_move WHERE id IN (<deleted_ids>);"
```

### 4. Option A: Switch app to scratch instance (fastest)

Update `ODOO_DB_HOST` in `.env` and restart Odoo.

### 5. Option B: pg_dump from scratch, restore into production

```bash
# Dump the specific tables from the scratch instance
pg_dump -h "$RESTORE_ENDPOINT" -U odoo_user -d invoice_agent \
  -t account_move -t account_move_line -t account_invoice_line \
  -Fc -f /tmp/restore_data.dump

# Restore into production
pg_restore -h "$RDS_HOST" -U odoo_user -d invoice_agent \
  --data-only --clean --if-exists /tmp/restore_data.dump
```

### 6. Cleanup

Delete the scratch RDS instance.

---

## Scenario D: Bad Deploy Rollback

**Target RTO:** < 5 minutes

### 1. Identify the last good tag

```bash
git log --oneline -10
# Find the commit before the bad deploy
```

### 2. Rollback invoice-ai (Python service)

```bash
# Redeploy with the previous image tag
PREVIOUS_TAG="<previous-commit-sha>"

INVOICE_AI_TAG="$PREVIOUS_TAG" docker compose \
  -f docker-compose.yml -f docker-compose.prod.yml \
  up -d --no-deps invoice-ai worker
```

### 3. Rollback Odoo addon (if bad commit is in custom_addons)

```bash
# Checkout the previous version of custom_addons
git checkout "$PREVIOUS_TAG" -- custom_addons/

# Rebuild and restart Odoo
docker compose up -d --build odoo

# Restore main branch after verification
git checkout main -- custom_addons/
```

### 4. Verify

```bash
curl -sf https://domain/web/health
curl -sf http://localhost:8100/healthz
```

---

## Measured RTO/RPO

| Drill Date | Scenario | RTO | RPO | Notes |
|------------|----------|-----|-----|-------|
| (fill in) | Full rebuild (Scenario B) | (fill in) | ~5 min | Measured during game day |
| (fill in) | PITR restore (Scenario C) | (fill in) | 5 min | Measured during game day |

---

## Quarterly Restore Drill

### Schedule

Open a GitHub issue every quarter using this template:

```
Title: Quarterly DR Restore Drill - [DATE]
Labels: security, infrastructure
```

### Procedure

1. Pick a team member who has NOT written this runbook.
2. Give them only this file and AWS credentials.
3. Start a timer.
4. They execute **Scenario B** (full rebuild) from scratch.
5. Every time they get stuck or deviate from the text → that's a documentation bug.
6. Fix the wording, commit, update the "Measured RTO/RPO" table above.
7. Repeat for **Scenario C** (PITR restore).

### Friction Log

After each drill, document every friction point:

| # | Friction Point | Fix | Status |
|---|---------------|-----|--------|
| (fill in during drill) | | | |

---

## Backup Verification Checklist

Run monthly to verify backups are intact:

```bash
# 1. List the latest backup
aws s3 ls s3://<backups-bucket>/daily/ --recursive | sort | tail -5

# 2. Download and verify it's a valid pg_dump
aws s3 cp s3://<backups-bucket>/daily/$(date +%Y%m%d)/invoice_agent.dump /tmp/verify.dump
pg_restore --list /tmp/verify.dump | head -20

# 3. Verify S3 versioning is enabled
aws s3api get-bucket-versioning --bucket <backups-bucket>

# 4. Verify RDS automated backups exist
aws rds describe-db-instances \
  --db-instance-identifier invoice-agent-prod \
  --query 'DBInstances[0].BackupRetentionPeriod'
# Should return 7
