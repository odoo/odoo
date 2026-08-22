# Runbook: Pipeline Error Rate High (PipelineErrorRateHigh)

**Alert**: `PipelineErrorRateHigh` — error rate > 2% for 5 minutes  
**Severity**: Critical  
**Grafana**: Invoice Agent — SLO Dashboard → Pipeline Error Rate panel

---

## What this means

The invoice-ai service is returning 5xx errors on more than 2% of requests.
This means invoices are failing extraction and the Odoo UI will show them
as errored or stuck in "extracting" state.

## Possible causes

1. **Claude API key revoked or invalid** — the most common cause during
   deployments or after billing issues
2. **Anthropic API outage** — check https://status.anthropic.com/
3. **RabbitMQ connection lost** — worker can't consume messages
4. **Redis connection lost** — LLM cache lookup fails
5. **RDS connection pool exhaustion** — RAG validation queries fail
6. **Memory pressure on EC2** — OOM kills the worker

## Immediate steps (< 5 minutes)

### 1. Check the worker logs

```bash
docker compose logs --tail=100 worker | grep -i error
```

### 2. Check Claude API key validity

```bash
# Test the API key directly
curl -s https://api.anthropic.com/v1/messages \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -H "content-type: application/json" \
  -d '{"model":"claude-opus-4-8","max_tokens":10,"messages":[{"role":"user","content":"ping"}]}'
```

If this returns a 401, the key is invalid. Rotate it in the AWS console
or `.env` file and restart:

```bash
docker compose restart worker invoice-ai
```

### 3. Check RabbitMQ health

```bash
docker compose exec rabbitmq rabbitmq-diagnostics -q ping
docker compose exec rabbitmq rabbitmqctl list_queues name messages consumers
```

If the `extract.request` queue has messages with 0 consumers, the worker
is down or can't connect.

### 4. Check Redis connectivity

```bash
docker compose exec worker python -c "import redis; r=redis.from_url('$REDIS_URL'); print(r.ping())"
```

### 5. Check disk space

```bash
df -h /
docker system df
```

If disk is full, prune Docker images:
```bash
docker system prune -af
```

## Resolution

- **Invalid API key**: rotate the key, restart worker, verify with a test
  invoice upload.
- **Anthropic outage**: wait for recovery. Messages in the queue will
  retry automatically via the retry ladder (5s → 30s → 5m).
- **Memory pressure**: restart the worker, investigate the root cause.
  Consider increasing memory limits in `docker-compose.prod.yml`.

## Verification

1. Watch Grafana: Pipeline Error Rate should drop to < 2% within 5 minutes
2. Check queue depth returns to 0
3. Upload a test invoice and verify it processes end-to-end

## Prevention

- Monitor the Claude API key expiration date
- Set up billing alerts in the Anthropic console
- Keep Prometheus alert rules as code (this repo)
