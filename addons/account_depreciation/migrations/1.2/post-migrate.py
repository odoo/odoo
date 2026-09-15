import logging

from odoo import SUPERUSER_ID, api
from odoo.db.schema import column_exists, table_exists
from odoo.tools import SQL

_logger = logging.getLogger(__name__)

TEMPLATE_COLUMNS = (
    "id",
    "name",
    "company_id",
    "active",
    "method",
    "method_number",
    "method_period",
    "method_progress_factor",
    "prorata_computation_type",
    "salvage_value_pct",
    "account_asset_id",
    "account_depreciation_id",
    "account_depreciation_expense_id",
    "journal_id",
    "analytic_distribution",
    "asset_properties_definition",
    "create_uid",
    "create_date",
    "write_uid",
    "write_date",
)
OLD_ACCOUNT_RELATION = "account_account_account_asset_rel"


RENAMED_BY_1_3 = {
    "state": "depreciation_state",
    "method": "depreciation_method",
    "method_number": "depreciation_duration",
    "method_period": "depreciation_period",
    "method_progress_factor": "depreciation_factor",
    "prorata_computation_type": "depreciation_prorata",
    "journal_id": "depreciation_journal_id",
}


def _column(cr, column):
    # 1.3's pre-migrate renames these columns, and every pre script of an upgrade
    # runs before any post script, so a database jumping past 1.2 reaches this
    # script with the new names already in place.
    renamed = RENAMED_BY_1_3.get(column)
    if renamed and column_exists(cr, "account_asset", renamed):
        return renamed
    return column


def migrate(cr, version):
    if not version or not column_exists(cr, "account_asset", "model_id"):
        return
    env = api.Environment(cr, SUPERUSER_ID, {})
    profile_by_template = _create_profiles(env)
    if not profile_by_template:
        return
    mapping = SQL(
        "(VALUES %s) AS map(template_id, profile_id)",
        SQL(", ").join(
            SQL("(%s, %s)", template_id, profile_id)
            for template_id, profile_id in profile_by_template.items()
        ),
    )
    cr.execute(
        SQL(
            """
            UPDATE account_asset asset
               SET depreciation_profile_id = map.profile_id
              FROM %s
             WHERE asset.model_id = map.template_id
            """,
            mapping,
        )
    )
    boards = cr.rowcount
    accounts = _move_account_links(env, mapping)
    moved = _repoint_generic_references(cr, mapping)
    cr.execute("UPDATE account_asset SET model_id = NULL WHERE model_id IS NOT NULL")
    cr.execute(
        SQL(
            "DELETE FROM account_asset WHERE id = ANY(%s)",
            list(profile_by_template),
        )
    )
    _logger.info(
        "account_depreciation: %d template(s) became profiles; %d board(s), "
        "%d account link(s) and %s repointed",
        len(profile_by_template),
        boards,
        accounts,
        moved,
    )


def _create_profiles(env):
    cr = env.cr
    cr.execute(
        SQL(
            "SELECT %s FROM account_asset WHERE %s = 'model' ORDER BY id",
            SQL(", ").join(
                SQL(
                    "%s AS %s",
                    SQL.identifier(_column(cr, column)),
                    SQL.identifier(column),
                )
                for column in TEMPLATE_COLUMNS
            ),
            SQL.identifier(_column(cr, "state")),
        )
    )
    templates = cr.dictfetchall()
    Profile = env["account.depreciation.profile"].with_context(
        tracking_disable=True, mail_create_nolog=True, active_test=False
    )
    profile_by_template = {}
    for template in templates:
        profile = Profile.create(
            {
                "name": template["name"],
                "company_id": template["company_id"],
                "active": template["active"],
                "depreciation_method": template["method"] or "linear",
                "depreciation_duration": template["method_number"],
                "depreciation_period": template["method_period"] or "12",
                "depreciation_factor": template["method_progress_factor"],
                "depreciation_prorata": template["prorata_computation_type"]
                or "constant_periods",
                "value_salvage_pct": template["salvage_value_pct"] or 0.0,
                "account_asset_id": template["account_asset_id"],
                "account_depreciation_id": template["account_depreciation_id"],
                "account_depreciation_expense_id": template[
                    "account_depreciation_expense_id"
                ],
                "depreciation_journal_id": template["journal_id"],
                "analytic_distribution": template["analytic_distribution"],
                "asset_properties_definition": template["asset_properties_definition"],
            }
        )
        profile_by_template[template["id"]] = profile.id
    Profile.flush_model()
    for template in templates:
        cr.execute(
            SQL(
                """
                UPDATE account_depreciation_profile
                   SET create_uid = %s, create_date = %s,
                       write_uid = %s, write_date = %s
                 WHERE id = %s
                """,
                template["create_uid"],
                template["create_date"],
                template["write_uid"],
                template["write_date"],
                profile_by_template[template["id"]],
            )
        )
    return profile_by_template


def _move_account_links(env, mapping):
    cr = env.cr
    if not table_exists(cr, OLD_ACCOUNT_RELATION):
        return 0
    relation = env["account.account"]._fields["depreciation_profile_ids"]
    cr.execute(
        SQL(
            """
            INSERT INTO %(relation)s (%(account)s, %(profile)s)
            SELECT old.account_account_id, map.profile_id
              FROM %(old)s old
              JOIN %(mapping)s ON map.template_id = old.account_asset_id
            ON CONFLICT DO NOTHING
            """,
            relation=SQL.identifier(relation.relation),
            account=SQL.identifier(relation.column1),
            profile=SQL.identifier(relation.column2),
            old=SQL.identifier(OLD_ACCOUNT_RELATION),
            mapping=mapping,
        )
    )
    linked = cr.rowcount
    cr.execute(SQL("DROP TABLE %s", SQL.identifier(OLD_ACCOUNT_RELATION)))
    env["account.account"].invalidate_model(["depreciation_profile_ids"])
    return linked


def _repoint_generic_references(cr, mapping):
    moved = {}
    for table, model_column in (
        ("ir_model_data", "model"),
        ("mail_message", "model"),
        ("mail_followers", "res_model"),
        ("mail_activity", "res_model"),
        ("ir_attachment", "res_model"),
    ):
        if not table_exists(cr, table):
            continue
        cr.execute(
            SQL(
                """
                UPDATE %(table)s record
                   SET %(model)s = 'account.depreciation.profile',
                       res_id = map.profile_id
                  FROM %(mapping)s
                 WHERE record.%(model)s = 'account.asset'
                   AND record.res_id = map.template_id
                """,
                table=SQL.identifier(table),
                model=SQL.identifier(model_column),
                mapping=mapping,
            )
        )
        moved[table] = cr.rowcount
    if column_exists(cr, "mail_activity", "res_model_id"):
        cr.execute(
            """
            UPDATE mail_activity
               SET res_model_id = (SELECT id FROM ir_model
                                    WHERE model = 'account.depreciation.profile')
             WHERE res_model = 'account.depreciation.profile'
            """
        )
    return ", ".join(f"{count} {table}" for table, count in moved.items())
