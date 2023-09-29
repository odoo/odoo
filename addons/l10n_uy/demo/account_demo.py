# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, models


class AccountChartTemplate(models.AbstractModel):

    _inherit = "account.chart.template"

    @api.model
    def _get_demo_data_move(self, company=False):
        """ Set the l10n_latam_document_number on demo invoices """
        move_data = super()._get_demo_data_move(company)
        if company.account_fiscal_country_id.code == 'UY':
            number = 1
            for move in move_data.values():
                if move['move_type'] in ('in_invoice', 'in_refund'):
                    move['l10n_latam_document_number'] = 'A' + f'{number:07d}'
                    number += 1

        return move_data
