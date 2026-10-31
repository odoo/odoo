#!/usr/bin/env bash
set -euo pipefail

: "${BASE_URL:=http://127.0.0.1:8069}"
: "${DB:=odoo}"
: "${LOGIN:?Set LOGIN to an active Odoo user login}"
: "${PASSWORD:?Set PASSWORD to the Odoo user password}"

for command in curl jq; do
    command -v "$command" >/dev/null 2>&1 || {
        echo "ERROR: $command is required." >&2
        exit 2
    }
done

BASE_URL="${BASE_URL%/}"
COOKIE_JAR="$(mktemp "${TMPDIR:-/tmp}/presenly-cookie.XXXXXX")"
LOGIN_RESPONSE="$(mktemp "${TMPDIR:-/tmp}/presenly-login.XXXXXX")"
STATUS_RESPONSE="$(mktemp "${TMPDIR:-/tmp}/presenly-status.XXXXXX")"
EXPIRED_RESPONSE="$(mktemp "${TMPDIR:-/tmp}/presenly-expired.XXXXXX")"
trap 'rm -f "$COOKIE_JAR" "$LOGIN_RESPONSE" "$STATUS_RESPONSE" "$EXPIRED_RESPONSE"' EXIT

rpc() {
    local url="$1"
    local body="$2"
    local output="$3"
    curl --fail-with-body --silent --show-error \
        -b "$COOKIE_JAR" -c "$COOKIE_JAR" \
        -H 'Content-Type: application/json' \
        -X POST "$url" --data "$body" >"$output"
}

echo "[1/5] Checking Odoo HTTP service at $BASE_URL ..."
curl --fail-with-body --silent --show-error \
    -o /dev/null "$BASE_URL/web/login"

echo "[2/5] Authenticating login $LOGIN on database $DB ..."
login_body="$(jq -cn \
    --arg db "$DB" --arg login "$LOGIN" --arg password "$PASSWORD" \
    '{jsonrpc:"2.0",method:"call",params:{db:$db,login:$login,password:$password},id:1}')"
rpc "$BASE_URL/web/session/authenticate" "$login_body" "$LOGIN_RESPONSE"
if jq -e '.error or (.result.uid == null)' "$LOGIN_RESPONSE" >/dev/null; then
    echo 'ERROR: Login failed:' >&2
    jq '{error, result: {uid: .result.uid, username: .result.username, db: .result.db}}' "$LOGIN_RESPONSE" >&2
    exit 1
fi
if ! grep -q $'\tsession_id\t' "$COOKIE_JAR"; then
    echo 'ERROR: Login response did not create a session_id cookie.' >&2
    exit 1
fi
uid="$(jq -r '.result.uid' "$LOGIN_RESPONSE")"
echo "      Authenticated as uid=$uid; session cookie received."

echo '[3/5] Checking Presenly attendance status ...'
rpc "$BASE_URL/api/presenly/v1/attendance/status" \
    '{"jsonrpc":"2.0","method":"call","params":{},"id":2}' \
    "$STATUS_RESPONSE"
if ! jq -e '
    .error == null
    and .result.success == true
    and (.result.data.employee_id | type == "number")
    and (.result.data.state == "checked_in" or .result.data.state == "checked_out")
    and (.result.data.can_check_in | type == "boolean")
    and (.result.data.can_check_out | type == "boolean")
    and (.result.data.available_work_locations | type == "array")
    and (.result.data | has("approved_leave") | not)
    and (.result.data | has("approved_permission") | not)
' "$STATUS_RESPONSE" >/dev/null; then
    echo 'ERROR: Presenly attendance-only status schema check failed:' >&2
    jq . "$STATUS_RESPONSE" >&2
    exit 1
fi
jq -r '"      employee_id=\(.result.data.employee_id) company_id=\(.result.data.company_id) state=\(.result.data.state) can_check_in=\(.result.data.can_check_in) can_check_out=\(.result.data.can_check_out)"' \
    "$STATUS_RESPONSE"

echo '[4/5] Destroying Odoo session ...'
rpc "$BASE_URL/web/session/destroy" \
    '{"jsonrpc":"2.0","method":"call","params":{},"id":3}' \
    /dev/null

echo '[5/5] Verifying the destroyed session is rejected ...'
rpc "$BASE_URL/api/presenly/v1/attendance/status" \
    '{"jsonrpc":"2.0","method":"call","params":{},"id":4}' \
    "$EXPIRED_RESPONSE" || true
if ! jq -e '.error != null' "$EXPIRED_RESPONSE" >/dev/null 2>&1; then
    echo 'ERROR: Destroyed session was unexpectedly accepted.' >&2
    jq . "$EXPIRED_RESPONSE" >&2
    exit 1
fi

echo 'PASS: Odoo login, session cookie, Presenly API, logout, and expired-session checks succeeded.'
