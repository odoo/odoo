
from odoo import models
from odoo.tools import SQL


class PolishTaxReportCustomHandler(models.AbstractModel):
    _inherit = 'l10n_pl.tax.report.handler'

    def _l10n_pl_get_query(
            self,
            report,
            options,
            move_to_group_by=None,
            additional_joined_table_for_aml_aggregates=None,
            additional_select_list=None,
            additional_joined_table=None,
    ) -> SQL:
        #  Override to include pos information needed for the JPK export

        if not move_to_group_by:
            move_to_group_by = SQL("COALESCE(session_move.id, account_move_line__move_id.id)")

        additional_joined_table_for_aml_aggregates = SQL(
            """
            LEFT JOIN pos_order ON pos_order.account_move = account_move_line__move_id.id
            LEFT JOIN pos_session ON pos_session.id = pos_order.session_id
            LEFT JOIN account_move session_move ON session_move.id = pos_session.move_id
            %s
            """,
            additional_joined_table_for_aml_aggregates or SQL()
        )

        additional_select_list = SQL(
            """,
            max(pos_order.id) as pos_order_id,
            max(pos_session.id) as pos_session_id
            %s
            """,
            additional_select_list or SQL()
        )

        additional_joined_table = SQL(
            """
            LEFT JOIN pos_order ON pos_order.account_move = account_move_line__move_id.id
            LEFT JOIN pos_session ON pos_session.move_id = account_move_line__move_id.id
            %s
            """,
            additional_joined_table or SQL()
        )

        return super()._l10n_pl_get_query(
            report,
            options,
            move_to_group_by=move_to_group_by,
            additional_joined_table_for_aml_aggregates=additional_joined_table_for_aml_aggregates,
            additional_select_list=additional_select_list,
            additional_joined_table=additional_joined_table,
        )
