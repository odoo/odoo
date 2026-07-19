from odoo import models
from odoo.tools.sql import SQL


class ResCompany(models.Model):
    _inherit = 'res.company'

    def _l10n_fr_pdp_get_f10_moves_query(self, account_ids, date_company_conditions):
        return SQL(
            '%s\n%s',
            super()._l10n_fr_pdp_get_f10_moves_query(account_ids, date_company_conditions),
            SQL(
                '''
                 UNION

                -- pos entry transactions --
                SELECT move.id
                  FROM account_move move
                 WHERE move.move_type = 'entry'
                   AND (move.pos_session_sales_id IS NOT NULL
                        OR move.pos_session_refunds_id IS NOT NULL)
                   AND move.reversed_pos_order_id IS NULL
                   AND %(date_company_conditions)s
                   AND move.state = 'posted'
                ''',
                date_company_conditions=date_company_conditions,
            ),
        )
