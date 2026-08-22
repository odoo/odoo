# Runbook: RDS Connections Near Cap (RDSConnectionsNearCap)

**Alert**: `RDSConnectionsNearCap` — connections > 85% of max_connections (200)  
**Severity**: Warning  
**Grafana**: Invoice Agent — SLO Dashboard → PostgreSQL Connections panel

---

## What this means

PostgreSQL connections are approaching the 200-connection limit configured
in the RDS parameter group. If connections hit 100%, new connections will
be refused and all services (Odoo, invoice-ai, worker) will fail with
"too many connections" errors.

## Possible causes

1. **Connection pool leak** — Odoo workers not releasing connections
2. **Too many Odoo workers** — each worker opens a DB connection
3. **RAG retrieval connection leak** — asyncpg pool not draining properly
4. **Monitoring tools** — postgres_exporter + Performance Insights add connections
5. **Database maintenance** — VACUUM, ANALYZE, or migration holding connections

## Immediate steps (< 5 minutes)

### 1. Check current connection count

```sql
-- Connect to RDS
psql -h <rds-endpoint> -U odoo_user -d odoo -c "
SELECT count(*), state 
FROM pg_stat_activity 
GROUP BY state;"
```

### 2. Identify connection consumers

```sql
-- Which applications are connected?
SELECT 
    application_name,
    client_addr,
    state,
    count(*) as connections
FROM pg_stat_activity 
GROUP BY application_name, client_addr, state
ORDER BY connections DESC;
```

### 3. Check for idle connections

```sql
-- Long-running idle connections (potential leaks)
SELECT 
    pid,
    application_name,
    state,
    state_change,
    now() - state_change as idle_duration
FROM pg_stat_activity 
WHERE state = 'idle'
ORDER BY idle_duration DESC
LIMIT 20;
```

### 4. Kill idle connections (if needed)

```sql
-- Kill connections idle for more than 10 minutes
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE state = 'idle'
  AND now() - state_change > interval '10 minutes'
  AND application_name NOT LIKE '%postgres_exporter%';
```

## Resolution

- **Connection pool leak**: Restart the Odoo service or the specific
  component leaking connections.
- **Too many workers**: Reduce `workers` in odoo.conf or scale up the
  RDS parameter group's `max_connections`.
- **RAG pool issue**: Check `invoice-ai` logs for pool exhaustion errors.
  Restart the service.
- **Scaling up**: Increase `max_connections` in the RDS parameter group
  (requires reboot). Note: higher connections = higher shared memory usage.

## Verification

1. Watch Grafana: connections should drop below 85% within 5 minutes
2. Check no new "too many connections" errors in service logs
3. Upload a test invoice to verify the pipeline works

## Prevention

- Monitor connection trends on the Grafana dashboard
- Set connection pool size limits in application code
- Use PgBouncer if connection count grows beyond RDS limits
