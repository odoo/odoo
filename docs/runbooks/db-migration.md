# Runbook: Database Migration — Local Postgres to RDS

> **Date:** 2026-08-18
> **Estimated downtime:** 5–15 minutes (during pg_restore)
> **Rollback time:** 5 minutes (switch back to local postgres)

---

## Prerequisites

1. **Terraform applied:** VPC, subnets, security groups, RDS all provisioned
2. **EC2 in app subnet:** Running in private subnet with NAT access
3. **RDS reachable:** `psql -h <rds-endpoint> -U odoo_admin -d odoo` succeeds from EC2
4. **Secrets Manager:** Both master and odoo-user secrets created
5. **Local stack running:** `docker compose up -d` with local postgres healthy

---

## Pre-Migration Checklist

- [ ] Terraform `apply` completed successfully
- [ ] RDS instance status is "available" in AWS Console
- [ ] RDS security group allows inbound 5432 from app security group
- [ ] Local database backup taken (Terraform creates snapshots)
- [ ] Maintenance window scheduled with stakeholders
- [ ] `pg_restore` installed on migration host (part of `postgresql-client`)

---

## Step 1: Verify RDS Connectivity

```bash
# From EC2 instance in app subnet
PGPASSWORD=$(aws secretsmanager get-secret-value \
  --secret-id odoo-invoice-agent-production/rds/master-password \
  --query 'SecretString' --output text | python3 -c "import sys,json; print(json.load(sys.stdin)['password'])") \
  psql -h $(terraform output -raw rds_hostname) \
       -p $(terraform output -raw rds_port) \
       -U odoo_admin -d odoo -c "SELECT 1;"
```

Expected: Returns `1`. If this fails, check VPC routing and security groups.

## Step 2: Snapshot Local Database

```bash
# Dump local database (already running)
docker compose exec -T db pg_dump -U odoo -Fc --no-owner -f /tmp/pre-migration.dump odoo

# Copy to local machine
docker compose cp db:/tmp/pre-migration.dump /tmp/pre-migration.dump
```

## Step 3: Stop Odoo

```bash
# Prevent new writes during migration
docker compose stop odoo
```

## Step 4: Final Consistent Dump

```bash
# With Odoo stopped, take the final dump
docker compose exec -T db pg_dump -U odoo -Fc --no-owner -f /tmp/final-migration.dump odoo

# Verify dump size (should be > 1MB for a real database)
docker compose exec -T db ls -la /tmp/final-migration.dump
```

## Step 5: Restore to RDS

```bash
# Get RDS password from Secrets Manager
RDS_PASS=$(aws secretsmanager get-secret-value \
  --secret-id odoo-invoice-agent-production/rds/master-password \
  --query 'SecretString' --output text | python3 -c "import sys,json; print(json.load(sys.stdin)['password'])")

RDS_HOST=$(terraform -chdir=infra/terraform output -raw rds_hostname)

# Copy dump to RDS host (via local psql client)
docker compose cp db:/tmp/final-migration.dump /tmp/final-migration.dump

# Restore
PGPASSWORD=$RDS_PASS pg_restore \
  -h $RDS_HOST \
  -U odoo_admin \
  -d odoo \
  --clean --if-exists \
  --no-owner --no-privileges \
  -j 4 \
  /tmp/final-migration.dump
```

**Time this step.** Record the duration in the table below.

| Metric | Value |
|--------|-------|
| Dump size | ___ MB |
| Restore duration | ___ seconds |
| account_move row count | ___ |
| ir_attachment row count | ___ |

## Step 6: Create Application User

```bash
PGPASSWORD=$RDS_PASS psql -h $RDS_HOST -U odoo_admin -d odoo <<-'SQL'
-- Create odoo_user (Odoo application role, NOT superuser)
DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'odoo_user') THEN
    CREATE ROLE odoo_user WITH LOGIN PASSWORD 'SET_PASSWORD_HERE';
  END IF;
END
$$;

GRANT CONNECT ON DATABASE odoo TO odoo_user;
GRANT USAGE ON SCHEMA public TO odoo_user;
GRANT CREATE ON SCHEMA public TO odoo_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO odoo_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO odoo_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO odoo_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO odoo_user;

-- Set password (store in Secrets Manager)
ALTER ROLE odoo_user PASSWORD 'SET_PASSWORD_HERE';
SQL
```

## Step 7: Repoint Odoo

```bash
# Update .env on EC2
cat >> /opt/odoo/.env << 'EOF'
ODOO_DB_HOST=<rds-endpoint>
ODOO_DB_PORT=5432
ODOO_DB_USER=odoo_user
ODOO_DB_PASSWORD=<from-secrets-manager>
EOF

# Or update using the RDS overlay
# docker-compose.prod.rds.yml provides these via env vars
```

## Step 8: Remove Local Postgres

```bash
# Switch to RDS overlay
docker compose -f docker-compose.yml -f docker-compose.prod.rds.yml up -d

# Verify Odoo connects to RDS
docker compose logs odoo | grep -i "database"
```

## Step 9: Validate

```bash
# Health check
curl -s -o /dev/null -w "%{http_code}" http://localhost:8069/web/login
# Expected: 200

# Run Odoo tests
docker compose exec -T odoo odoo-bin --test-tags /invoice_agent \
  -d odoo --stop-after-init --log-level=test

# Run pytest suite
docker compose exec -T invoice-ai pytest tests/ -v
```

## Step 10: Enable Monitoring

```bash
# Verify Performance Insights is enabled
aws rds describe-db-instances \
  --db-instance-identifier odoo-invoice-agent-production-db \
  --query 'DBInstances[0].PerformanceInsightsEnabled'
# Expected: true

# Verify enhanced monitoring
aws rds describe-db-instances \
  --db-instance-identifier odoo-invoice-agent-production-db \
  --query 'DBInstances[0].MonitoringInterval'
# Expected: 60
```

---

## Rollback Procedure

If something goes wrong:

```bash
# 1. Switch back to local postgres
#    a. Remove RDS env vars from .env
#    b. Restore local postgres from snapshot
docker compose -f docker-compose.yml up -d db
sleep 15  # wait for postgres to be healthy

# 2. Restore local database from pre-migration dump
docker compose cp /tmp/pre-migration.dump db:/tmp/pre-migration.dump
docker compose exec -T db pg_restore -U odoo -d odoo --clean --if-exists --no-owner /tmp/pre-migration.dump

# 3. Restart Odoo (original compose file)
docker compose up -d odoo

# 4. Verify
curl -s -o /dev/null -w "%{http_code}" http://localhost:8069/web/login
# Expected: 200
```

---

## Post-Migration Tasks

- [ ] Update `docs/deployment.md` with new RDS endpoint
- [ ] Remove SSH port 22 from security group (use SSM instead)
- [ ] Test SSM Session Manager access to EC2
- [ ] Verify CloudWatch alarms fire correctly
- [ ] Test automated backup restoration from RDS snapshot
- [ ] Update CI/CD deploy workflow to use RDS overlay
- [ ] Commit Terraform files: `git add -f infra/`
- [ ] Commit docs: `git add -f docs/architecture.md docs/runbooks/db-migration.md`
