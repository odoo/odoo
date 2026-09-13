import re
from collections import defaultdict
from datetime import UTC, datetime

from odoo import api, models
from odoo.libs.datetime import timezone
from odoo.libs.debug_log import DebugLog
from odoo.tools import SQL

_debug = DebugLog(__name__)


class KpiProvider(models.AbstractModel):
    _inherit = "kpi.provider"

    @api.model
    def get_account_reports_kpi_summary(self):
        return get_kpi_summary(self.env.cr, self.env.uid)

    @api.model
    def get_kpi_summary(self):
        result = super().get_kpi_summary()
        result.extend(self.get_account_reports_kpi_summary())
        return result


def _tax_return_grouping_key(external_ids, return_info):
    external_id = ""

    # Determine the external identifier used to categorize the tax returns:
    # - use the identifier of the root report if any,
    # - otherwise use the identifier of the report,
    # - otherwise use the identifier of the return type.
    external_id = external_ids.get(("account.report", return_info["root_report_id"]))
    if not external_id:
        external_id = external_ids.get(("account.report", return_info["report_id"]))
    if not external_id:
        external_id = external_ids.get(
            ("account.return.type", return_info["return_type_id"])
        )
    if not external_id:
        external_id = return_info["tax_return_name"]

    # Special case for l10n_eu_oss_reports.* that are all merged together.
    if external_id.startswith("l10n_eu_oss_reports."):
        external_id = "l10n_eu_oss_reports"

    # property names must match odoo.orm.utils.regex_alphanumeric
    return re.sub(r"[^a-z0-9_]", "_", external_id.lower())


def _tax_returns_get_value(tax_returns):
    for tax_return in tax_returns:
        if tax_return["is_late"]:
            return "late"
        elif not tax_return["is_completed"]:
            if tax_return["state"] in ("reviewed", "submitted"):
                return "to_submit"
            elif tax_return["in_next_3_months"]:
                return "to_do"
            else:
                return "longterm"
    return "done"


def get_kpi_summary(cr, uid):
    """Retrieve the status of pending tax returns grouped by report or return type.

    :param cr: database cursor
    :param int uid: user the deadlines are evaluated for (timezone and language)
    :return: list of ``{'id', 'name', 'type', 'value'}`` dicts, one per return group
    :rtype: list
    """
    # Deliberately bypasses the ORM: KPI summaries can then be served without
    # loading a registry, which is faster on multi-database servers.
    expected_columns = {
        "account_return.date_deadline",
        "account_return.is_completed",
        "account_return.type_id",
        "account_return_type.report_id",
        "account_report.root_report_id",
    }
    cr.execute(
        SQL(
            """
        SELECT table_name || '.' || column_name
          FROM information_schema.columns
         WHERE table_name || '.' || column_name IN %(columns)s
    """,
            columns=tuple(expected_columns),
        )
    )
    existing_columns = {x[0] for x in cr.fetchall()}
    if _debug.logic.enabled:
        _debug.logic(
            "tax_return_kpi_columns_checked",
            uid=uid,
            missing=sorted(expected_columns - existing_columns),
        )
    if expected_columns - existing_columns:
        # Needed columns are not present -> module is not installed
        return []

    cr.execute(
        SQL("""
        SELECT model, res_id, module || '.' || name
          FROM ir_model_data
         WHERE model IN ('account.report', 'account.return.type')
           AND module != '__export__'
    """)
    )
    external_ids = {
        (model, res_id): complete_name for model, res_id, complete_name in cr.fetchall()
    }
    _debug.perf.count("tax_return_external_ids_fetched", rows=len(external_ids))

    # The user's own "today", resolved in Python. Reading the timezone costs one
    # indexed lookup and settles three things the SQL could not:
    #  * ``AT TIME ZONE`` only accepts the timezone names *PostgreSQL* knows,
    #    and Odoo's tz dropdown offers a wider set (every zoneinfo name, legacy
    #    aliases included). A user whose profile said 'Asia/Calcutta' got
    #    InvalidParameterValue instead of a KPI;
    #  * the conversion ran backwards. ``now`` is naive, so
    #    ``now AT TIME ZONE tz`` read it as wall-clock time *in* the user's zone
    #    and produced an instant, which ``::date`` then rendered in the
    #    *session's* timezone -- at 20:00 UTC that answered 2026-08-15 for a
    #    Tokyo user whose date was already the 16th;
    #  * ``::date`` on a timestamptz depends on the session's TimeZone, which
    #    Odoo never sets, so the same query answered differently on two servers.
    cr.execute(
        SQL(
            """
        SELECT partner.tz
          FROM res_users u
          JOIN res_partner partner ON partner.id = u.partner_id
         WHERE u.id = %(uid)s
    """,
            uid=uid,
        )
    )
    row = cr.fetchone()
    # Using python-generated dates to respect what freezegun has frozen in tests
    today = datetime.now(UTC).astimezone(timezone((row and row[0]) or "UTC")).date()
    _debug.logic(
        "tax_return_kpi_today",
        uid=uid,
        tz=(row and row[0]) or "UTC",
        today=today,
        external_ids=len(external_ids),
    )
    cr.execute(
        SQL(
            """
        SELECT return.id return_id,
               type.id return_type_id,
               report.id report_id,
               root_report.id root_report_id,
               COALESCE(report.name->>partner.lang,
                        report.name->>'en_US',
                        type.name->>partner.lang,
                        type.name->>'en_US') tax_return_name,
               return.date_deadline <= %(today)s is_late,
               return.date_deadline <= %(today)s + INTERVAL '3 months' in_next_3_months,
               return.is_completed,
               return.state
          FROM account_return return
          JOIN res_users u ON u.id = %(uid)s
          JOIN res_partner partner ON partner.id = u.partner_id
          JOIN account_return_type type ON return.type_id = type.id
     LEFT JOIN account_report report ON type.report_id = report.id
     LEFT JOIN account_report root_report ON report.root_report_id = root_report.id
         WHERE (NOT return.is_completed
               OR return.date_deadline >= %(today)s)
               AND EXISTS (
                   SELECT 1
                     FROM account_return_res_company_rel arc
                     JOIN res_company_users_rel rcu
                       ON rcu.cid = arc.res_company_id
                    WHERE arc.account_return_id = return.id
                      AND rcu.user_id = %(uid)s
               )
      ORDER BY return.date_deadline NULLS LAST, return.id
    """,
            uid=uid,
            today=today,
        )
    )
    returns_by_external_id = defaultdict(list)
    for return_info in cr.dictfetchall():
        key = _tax_return_grouping_key(external_ids, return_info)
        returns_by_external_id[key].append(return_info)
    if _debug.pipeline.enabled:
        _debug.pipeline(
            "tax_returns_grouped",
            uid=uid,
            groups=len(returns_by_external_id),
            returns=sum(len(returns) for returns in returns_by_external_id.values()),
        )

    return [
        {
            "id": f"account_return.{external_id}",
            "name": tax_returns[0]["tax_return_name"],
            "type": "return_status",
            "value": _tax_returns_get_value(tax_returns),
        }
        for external_id, tax_returns in returns_by_external_id.items()
    ]
