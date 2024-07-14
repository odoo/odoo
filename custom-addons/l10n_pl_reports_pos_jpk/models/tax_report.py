
from odoo import models


class PolishTaxReportCustomHandler(models.AbstractModel):
    _inherit = 'l10n_pl.tax.report.handler'

    def _l10n_pl_get_query_parts(self):
        #  Override to include pos information needed for the JPK export
        dict_query_parts = super()._l10n_pl_get_query_parts()

        dict_query_parts.update(
            {
                'select_query_part': dict_query_parts.get('select_query_part', "") + """
                                        , max(pos_order.id) as pos_order_id,
                                        max(pos_session.id) as pos_session_id
                                    """,
                'from_query_part':  dict_query_parts.get('from_query_part', "") + """
                                        LEFT JOIN pos_order ON pos_order.account_move = "account_move_line__move_id".id
                                        LEFT JOIN pos_session ON pos_session.move_id = "account_move_line__move_id".id
                                    """,
                'from_moves_to_aggregate': "COALESCE(session_move.id, account_move_line__move_id.id)",
                'additional_joins_for_aml_aggregate': """
                    LEFT JOIN pos_order ON pos_order.account_move = account_move_line__move_id.id
                    LEFT JOIN pos_session ON pos_session.id = pos_order.session_id
                    LEFT JOIN account_move session_move ON session_move.id = pos_session.move_id
                """
            }
        )

        return dict_query_parts
