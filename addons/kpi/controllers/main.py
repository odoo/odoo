import json
import re

from passlib.context import CryptContext

from odoo.http import Controller, request, route
from odoo.sql_db import db_connect

INDEX_SIZE = 8
KEY_CRYPT_CONTEXT = CryptContext(['pbkdf2_sha512'], pbkdf2_sha512__rounds=6000)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _json_response(data, status=200):
    return request.make_response(
        json.dumps(data, default=str),
        [('Content-Type', 'application/json')],
        status=status,
    )


def _check_api_key(cr, api_key):
    """Verify *api_key* and return the owning ``user_id``, or *None*."""
    index = api_key[:INDEX_SIZE]
    cr.execute("""
        SELECT user_id, key
        FROM res_users_apikeys k
            INNER JOIN res_users u ON u.id = k.user_id
        WHERE u.active
            AND k.index = %s
            AND (k.expiration_date IS NULL OR k.expiration_date >= now() AT TIME ZONE 'utc')
    """, [index])
    for user_id, hashed_key in cr.fetchall():
        if KEY_CRYPT_CONTEXT.verify(api_key, hashed_key):
            return user_id
    return None


def _authenticate(database, api_key):
    """Return ``(cursor, uid)`` or ``(response, None)``."""
    db_name = database or request.db
    if not db_name:
        return _json_response({'error': 'No database specified'}, 400), None
    if not api_key:
        return _json_response({'error': 'Missing api_key parameter'}, 401), None
    cr = db_connect(db_name).cursor()
    uid = _check_api_key(cr, api_key)
    if not uid:
        cr.close()
        return _json_response({'error': 'Invalid api_key'}, 403), None
    return cr, uid


def _table_exists(cr, table_name):
    cr.execute("""
        SELECT 1 FROM pg_class c
        WHERE c.relname = %s
            AND c.relkind IN ('r', 'v', 'm')
            AND c.relnamespace = current_schema::regnamespace
    """, [table_name])
    return cr.fetchone() is not None


def _get_translated(value, lang='en_US'):
    """Extract a human-readable string from a column that may be plain text
    or a jsonb translation dict (Odoo 17+)."""
    if isinstance(value, dict):
        return value.get(lang) or value.get('en_US') or next(iter(value.values()), '')
    return value or ''


# ---------------------------------------------------------------------------
# KPI summary providers (one function per contributing module)
# ---------------------------------------------------------------------------

def _kpi_mail_activities(cr, uid):
    """Port of ``mail`` KPI provider — activity count by type."""
    if not _table_exists(cr, 'mail_activity'):
        return []
    cr.execute("""
        SELECT
            COALESCE(imd.module || '.' || imd.name, mat.name::text) AS identifier,
            mat.name AS type_name,
            COUNT(*) AS cnt
        FROM mail_activity ma
        JOIN mail_activity_type mat ON ma.activity_type_id = mat.id
        LEFT JOIN ir_model_data imd
            ON imd.model = 'mail.activity.type'
            AND imd.res_id = mat.id
            AND imd.module != '__export__'
        WHERE mat.kpi_provider_visibility = 'all'
           OR (mat.kpi_provider_visibility = 'own' AND ma.user_id = %s)
        GROUP BY mat.id, mat.name, imd.module, imd.name
    """, [uid])
    results = []
    for identifier, type_name, cnt in cr.fetchall():
        normalized = re.sub(r'[^a-z0-9]', '_', str(identifier).lower())
        results.append({
            'id': 'mail_activity_type.' + normalized,
            'name': _get_translated(type_name),
            'type': 'integer',
            'value': cnt,
        })
    return results


def _kpi_account(cr):
    """Port of ``account`` KPI provider — moves to process by journal type."""
    if not _table_exists(cr, 'account_move'):
        return []

    # Build WHERE clause based on available columns
    cr.execute("""
        SELECT column_name FROM information_schema.columns
        WHERE table_name = 'account_move'
            AND column_name IN ('review_state', 'statement_line_id')
            AND table_schema = current_schema
    """)
    cols = {row[0] for row in cr.fetchall()}

    conditions = ["am.state = 'draft'"]
    join_extra = ""
    if 'review_state' in cols:
        conditions.append("(am.state = 'posted' AND am.review_state IN ('todo', 'anomaly'))")
    if 'statement_line_id' in cols and _table_exists(cr, 'account_bank_statement_line'):
        join_extra = "LEFT JOIN account_bank_statement_line absl ON am.statement_line_id = absl.id"
        conditions.append(
            "(am.state = 'posted' AND aj.type = 'bank' AND absl.is_reconciled = FALSE)")

    cr.execute("""
        SELECT aj.type, COUNT(DISTINCT am.id)
        FROM account_move am
        JOIN account_journal aj ON am.journal_id = aj.id
        {join}
        WHERE {where}
        GROUP BY aj.type
    """.format(join=join_extra, where=" OR ".join(conditions)))
    move_counts = cr.fetchall()

    # Journal type labels from selection field
    cr.execute("""
        SELECT imfs.value, imfs.name
        FROM ir_model_fields_selection imfs
        JOIN ir_model_fields imf ON imfs.field_id = imf.id
        WHERE imf.model = 'account.journal' AND imf.name = 'type'
    """)
    type_names = {v: _get_translated(n) for v, n in cr.fetchall()}

    return [{
        'id': f'account_journal_type.{jtype}',
        'name': type_names.get(jtype, jtype),
        'type': 'integer',
        'value': cnt,
    } for jtype, cnt in move_counts]


def _kpi_documents(cr):
    """Port of ``documents`` KPI provider — inbox document count."""
    if not _table_exists(cr, 'documents_document'):
        return []
    # Resolve the inbox folder via its xml-id
    cr.execute("""
        SELECT res_id FROM ir_model_data
        WHERE module = 'documents' AND name = 'document_inbox_folder'
    """)
    row = cr.fetchone()
    if not row:
        return []
    inbox_id = row[0]

    # Check the folder is active
    cr.execute("SELECT active FROM documents_folder WHERE id = %s", [inbox_id])
    folder = cr.fetchone()
    if not folder or not folder[0]:
        return []

    # Count documents in inbox and its children (excluding sub-folders)
    cr.execute("""
        WITH RECURSIVE children AS (
            SELECT id FROM documents_folder WHERE id = %s
            UNION ALL
            SELECT f.id FROM documents_folder f JOIN children c ON f.parent_folder_id = c.id
        )
        SELECT COUNT(*)
        FROM documents_document d
        WHERE d.folder_id IN (SELECT id FROM children)
            AND d.type != 'folder'
    """, [inbox_id])
    return [{
        'id': 'documents.inbox',
        'name': 'Inbox',
        'type': 'integer',
        'value': cr.fetchone()[0],
    }]


def _kpi_account_reports(cr):
    """Port of ``account_reports`` KPI provider — tax return statuses."""
    if not _table_exists(cr, 'account_return'):
        return []
    cr.execute("""
        SELECT
            ar.id,
            ar.date_deadline,
            ar.is_completed,
            ar.state,
            COALESCE(
                (SELECT imd.module || '.' || imd.name
                 FROM ir_model_data imd
                 WHERE imd.model = 'account.report' AND imd.res_id = rep.root_report_id
                     AND imd.module != '__export__'
                 LIMIT 1),
                (SELECT imd.module || '.' || imd.name
                 FROM ir_model_data imd
                 WHERE imd.model = 'account.report' AND imd.res_id = art.report_id
                     AND imd.module != '__export__'
                 LIMIT 1),
                (SELECT imd.module || '.' || imd.name
                 FROM ir_model_data imd
                 WHERE imd.model = 'account.return.type' AND imd.res_id = ar.type_id
                     AND imd.module != '__export__'
                 LIMIT 1),
                COALESCE(rep.name::text, art.name::text)
            ) AS external_id,
            COALESCE(rep.name, art.name) AS display_name
        FROM account_return ar
        JOIN account_return_type art ON ar.type_id = art.id
        LEFT JOIN account_report rep ON art.report_id = rep.id
        WHERE ar.is_completed = FALSE
           OR ar.date_deadline >= (now() AT TIME ZONE 'utc')::date
        ORDER BY ar.date_deadline
    """)
    rows = cr.fetchall()

    # Group by external_id (mimics the Python grouped() logic)
    from collections import OrderedDict
    groups = OrderedDict()
    for _id, deadline, is_completed, state, ext_id, display_name in rows:
        ext_id_str = str(ext_id or '')
        if ext_id_str.startswith('l10n_eu_oss_reports.'):
            ext_id_str = 'l10n_eu_oss_reports'
        key = re.sub(r'[^a-z0-9_]', '_', ext_id_str.lower())
        groups.setdefault(key, []).append({
            'deadline': deadline,
            'is_completed': is_completed,
            'state': state,
            'display_name': _get_translated(display_name),
        })

    today = cr.execute("SELECT current_date")
    today = cr.fetchone()[0]
    from datetime import timedelta
    three_months = today + timedelta(days=90)

    results = []
    for ext_id, returns in groups.items():
        # Determine worst status across returns in this group
        value = 'done'
        for r in returns:
            if r['deadline'] and r['deadline'] <= today:
                value = 'late'
                break
            if not r['is_completed']:
                if r['state'] in ('reviewed', 'submitted'):
                    value = 'to_submit'
                    break
                if r['deadline'] and r['deadline'] <= three_months:
                    value = 'to_do'
                    break
                value = 'longterm'
                break

        results.append({
            'id': f'account_return.{ext_id}',
            'name': returns[0]['display_name'],
            'type': 'return_status',
            'value': value,
        })
    return results


# ---------------------------------------------------------------------------
# Controller
# ---------------------------------------------------------------------------

class KpiController(Controller):

    @route('/kpi/internal_users', type='http', auth='none', save_session=False)
    def internal_users(self, database=None, api_key=None):
        cr, uid = _authenticate(database, api_key)
        if uid is None:
            return cr
        with cr:
            cr.execute("""
                SELECT p.name, u.login,
                    (SELECT MAX(l.create_date) FROM res_users_log l WHERE l.create_uid = u.id)
                        AS login_date
                FROM res_users u
                JOIN res_partner p ON u.partner_id = p.id
                WHERE u.active AND u.share IS NOT TRUE
            """)
            users = [{
                'name': _get_translated(name),
                'login': login,
                'login_date': login_date,
            } for name, login, login_date in cr.fetchall()]
            return _json_response(users)

    @route('/kpi/summary', type='http', auth='none', save_session=False)
    def kpi_summary(self, database=None, api_key=None):
        cr, uid = _authenticate(database, api_key)
        if uid is None:
            return cr
        with cr:
            result = []
            result.extend(_kpi_mail_activities(cr, uid))
            result.extend(_kpi_account(cr))
            result.extend(_kpi_account_reports(cr))
            result.extend(_kpi_documents(cr))
            return _json_response(result)

    @route('/kpi/database_uuid', type='http', auth='none', save_session=False)
    def database_uuid(self, database=None, api_key=None):
        cr, uid = _authenticate(database, api_key)
        if uid is None:
            return cr
        with cr:
            cr.execute("SELECT value FROM ir_config_parameter WHERE key = 'database.uuid'")
            row = cr.fetchone()
            return _json_response({'uuid': row[0] if row else None})

    @route('/kpi/remove_users', type='http', auth='none', save_session=False, methods=['POST'], csrf=False)
    def remove_users(self, database=None, api_key=None):
        cr, uid = _authenticate(database, api_key)
        if uid is None:
            return cr
        with cr:
            data = json.loads(request.httprequest.data)
            logins = data.get('logins', [])
            if not logins:
                return _json_response({'error': 'No logins provided'}, 400)
            cr.execute(
                "UPDATE res_users SET active = FALSE WHERE login IN %s RETURNING login",
                [tuple(logins)],
            )
            deactivated = [row[0] for row in cr.fetchall()]
            return _json_response({'deactivated': deactivated})
