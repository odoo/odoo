#!/opt/rkadmin/venv/bin/python3
"""
Odoo → Google Sheets sync
Runs every 10 min via cron but only syncs when POS session is active.
Triggers: session open, or closed within the last 30 minutes.
Structure: rkpos-data/club26/YYYYMMDD/orders, sales, attendance
"""
import sys
import logging
from datetime import date

import psycopg2
import gspread
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────────────
DB = {
    "host":     "localhost",
    "port":     5432,
    "user":     "odoo",
    "password": "odoo",
    "dbname":   "odoo-db",
}
TOKEN_FILE       = "/opt/rkadmin/rkpos/token.json"
ROOT_FOLDER_NAME = "rkpos-data"
SITE_FOLDER_NAME = "club26"
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]
TODAY = date.today().strftime("%Y%m%d")
# ─────────────────────────────────────────────────────────────────────────────


def should_sync(conn):
    """Return True if a POS session is open or closed within the last 30 min."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT COUNT(*) FROM pos_session
            WHERE start_at::date = CURRENT_DATE
            AND (
                state = 'opened'
                OR (stop_at IS NOT NULL AND stop_at > NOW() - INTERVAL '30 minutes')
            )
        """)
        return cur.fetchone()[0] > 0


def fetch_pos_orders(conn):
    with conn.cursor() as cur:
        cur.execute("""
            SELECT
                po.name                                                            AS "Order",
                to_char(po.date_order AT TIME ZONE 'UTC', 'YYYY-MM-DD HH24:MI')  AS "Date",
                COALESCE(rp.name, 'Walk-in')                                      AS "Customer",
                COALESCE(rr_emp.name, '')                                          AS "Cashier",
                pt.name                                                            AS "Product",
                pol.qty                                                            AS "Qty",
                pol.price_unit                                                     AS "Unit Price",
                pol.price_subtotal_incl                                            AS "Line Total",
                po.amount_total                                                    AS "Order Total",
                po.state                                                           AS "State"
            FROM pos_order po
            JOIN pos_order_line     pol    ON pol.order_id   = po.id
            JOIN product_product    pp     ON pp.id          = pol.product_id
            JOIN product_template   pt     ON pt.id          = pp.product_tmpl_id
            LEFT JOIN res_partner      rp      ON rp.id      = po.partner_id
            LEFT JOIN hr_employee      he      ON he.id      = po.employee_id
            LEFT JOIN resource_resource rr_emp ON rr_emp.id  = he.resource_id
            WHERE po.date_order::date = CURRENT_DATE
            ORDER BY po.date_order, po.name, pol.id
        """)
        cols = [d[0] for d in cur.description]
        rows = [[str(c) if c is not None else "" for c in row] for row in cur.fetchall()]
        return cols, rows


def fetch_sales(conn):
    with conn.cursor() as cur:
        cur.execute("""
            SELECT
                so.name                                                            AS "Order",
                to_char(so.date_order AT TIME ZONE 'UTC', 'YYYY-MM-DD HH24:MI')  AS "Date",
                COALESCE(rp.name, '')                                              AS "Customer",
                COALESCE(rp_user.name, '')                                         AS "Salesperson",
                pt.name                                                            AS "Product",
                sol.product_uom_qty                                                AS "Qty",
                sol.price_unit                                                     AS "Unit Price",
                sol.price_subtotal                                                 AS "Line Total",
                so.amount_total                                                    AS "Order Total",
                so.state                                                           AS "State"
            FROM sale_order so
            JOIN sale_order_line  sol     ON sol.order_id    = so.id
            JOIN product_product  pp      ON pp.id           = sol.product_id
            JOIN product_template pt      ON pt.id           = pp.product_tmpl_id
            LEFT JOIN res_partner rp      ON rp.id           = so.partner_id
            LEFT JOIN res_users   ru      ON ru.id           = so.user_id
            LEFT JOIN res_partner rp_user ON rp_user.id      = ru.partner_id
            WHERE so.date_order::date = CURRENT_DATE
            ORDER BY so.date_order, so.name, sol.id
        """)
        cols = [d[0] for d in cur.description]
        rows = [[str(c) if c is not None else "" for c in row] for row in cur.fetchall()]
        return cols, rows


def fetch_attendance(conn):
    with conn.cursor() as cur:
        cur.execute("""
            SELECT
                rr.name                                                           AS "Employee",
                to_char(ha.check_in  AT TIME ZONE 'UTC', 'YYYY-MM-DD HH24:MI')  AS "Check In",
                to_char(ha.check_out AT TIME ZONE 'UTC', 'YYYY-MM-DD HH24:MI')  AS "Check Out",
                ROUND(COALESCE(ha.worked_hours, 0)::numeric, 2)                  AS "Worked Hours"
            FROM hr_attendance ha
            JOIN hr_employee      he ON he.id  = ha.employee_id
            JOIN resource_resource rr ON rr.id = he.resource_id
            WHERE ha.check_in::date = CURRENT_DATE
            ORDER BY ha.check_in
        """)
        cols = [d[0] for d in cur.description]
        rows = [[str(c) if c is not None else "" for c in row] for row in cur.fetchall()]
        return cols, rows


def fetch_sessions(conn):
    with conn.cursor() as cur:
        cur.execute("""
            SELECT
                ps.name                                                                    AS "Session",
                to_char(ps.start_at AT TIME ZONE 'UTC', 'YYYY-MM-DD HH24:MI')            AS "Opened",
                COALESCE(to_char(ps.stop_at AT TIME ZONE 'UTC', 'YYYY-MM-DD HH24:MI'),'-') AS "Closed",
                ps.state                                                                   AS "State",
                COALESCE(ps.cash_register_balance_start, 0)                               AS "Opening Balance",
                COALESCE(SUM(CASE WHEN ppm.is_cash_count     THEN pp.amount ELSE 0 END), 0) AS "Cash Sales",
                COALESCE(SUM(CASE WHEN NOT ppm.is_cash_count THEN pp.amount ELSE 0 END), 0) AS "Card Sales",
                COALESCE(SUM(pp.amount), 0)                                               AS "Total Sales",
                COALESCE(ps.cash_register_balance_start, 0)
                  + COALESCE(ps.cash_real_transaction, 0)                                   AS "Expected Cash",
                COALESCE(ps.cash_register_balance_end_real, 0)                            AS "Actual Closing",
                COALESCE(ps.cash_register_balance_end_real, 0)
                  - (COALESCE(ps.cash_register_balance_start, 0)
                  + COALESCE(ps.cash_real_transaction, 0))                                  AS "Difference",
                COUNT(DISTINCT po.id)                                                     AS "Orders"
            FROM pos_session ps
            LEFT JOIN pos_order po ON po.session_id = ps.id
                AND po.state IN ('paid', 'done', 'invoiced')
            LEFT JOIN pos_payment pp ON pp.pos_order_id = po.id
            LEFT JOIN pos_payment_method ppm ON ppm.id = pp.payment_method_id
            WHERE ps.start_at::date = CURRENT_DATE
            GROUP BY ps.id, ps.name, ps.start_at, ps.stop_at, ps.state,
                     ps.cash_register_balance_start, ps.cash_register_balance_end_real,
                     ps.cash_real_transaction
            ORDER BY ps.start_at
        """)
        cols = [d[0] for d in cur.description]
        rows = [[str(c) if c is not None else "" for c in row] for row in cur.fetchall()]
        return cols, rows


def find_or_create_folder(drive, name, parent_id):
    q = (
        f"name='{name}' and mimeType='application/vnd.google-apps.folder' "
        f"and '{parent_id}' in parents and trashed=false"
    )
    results = drive.files().list(q=q, fields="files(id)").execute()
    files = results.get("files", [])
    if files:
        return files[0]["id"]
    meta = {
        "name": name,
        "mimeType": "application/vnd.google-apps.folder",
        "parents": [parent_id],
    }
    folder = drive.files().create(body=meta, fields="id").execute()
    log.info(f"Created folder: {name}")
    return folder["id"]


def find_or_create_spreadsheet(drive, gc, name, folder_id):
    q = (
        f"name='{name}' and mimeType='application/vnd.google-apps.spreadsheet' "
        f"and '{folder_id}' in parents and trashed=false"
    )
    results = drive.files().list(q=q, fields="files(id)").execute()
    files = results.get("files", [])
    if files:
        return gc.open_by_key(files[0]["id"])
    meta = {
        "name": name,
        "mimeType": "application/vnd.google-apps.spreadsheet",
        "parents": [folder_id],
    }
    sheet_file = drive.files().create(body=meta, fields="id").execute()
    log.info(f"Created spreadsheet: {name}")
    return gc.open_by_key(sheet_file["id"])


def write_sheet(spreadsheet, headers, rows):
    ws = spreadsheet.sheet1
    ws.clear()
    ws.update([headers] + rows)
    log.info(f"  → {len(rows)} rows written")


def main():
    conn = psycopg2.connect(**DB)

    try:
        if not should_sync(conn):
            log.info("No active POS session — skipping sync.")
            return

        log.info(f"POS session active — syncing for {TODAY}")

        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            with open(TOKEN_FILE, "w") as f:
                f.write(creds.to_json())
        gc    = gspread.authorize(creds)
        drive = build("drive", "v3", credentials=creds)

        # Build folder structure: rkpos-data/club26/YYYYMMDD
        root_id = find_or_create_folder(drive, ROOT_FOLDER_NAME, "root")
        site_id = find_or_create_folder(drive, SITE_FOLDER_NAME, root_id)
        date_id = find_or_create_folder(drive, TODAY, site_id)

        for label, fetcher in [
            ("sessions",   fetch_sessions),
            ("orders",     fetch_pos_orders),
            ("sales",      fetch_sales),
            ("attendance", fetch_attendance),
        ]:
            try:
                log.info(f"Syncing {label}...")
                headers, rows = fetcher(conn)
                ss = find_or_create_spreadsheet(drive, gc, label, date_id)
                write_sheet(ss, headers, rows)
            except psycopg2.errors.UndefinedTable:
                conn.rollback()
                log.warning(f"  Skipping {label} — module not installed.")

        log.info("Sync complete.")

    finally:
        conn.close()


if __name__ == "__main__":
    main()
