# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, api


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @api.model
    def _get_demo_data_move(self, company=False):
        """ Set the l10n_latam_document_number on demo invoices """
        move_data = super()._get_demo_data_move(company)
        if company.account_fiscal_country_id.code == 'BR':
            number = 0
            for move in move_data.values():
                # vendor bills and refund must be manually numbered (l10n_br uses the standard AccountMove._is_manual_document_number())
                if move['move_type'] in ('in_invoice', 'in_refund'):
                    move['l10n_latam_document_number'] = f'{number:08d}'
                    number += 1

        return move_data
