import logging
from odoo import api, models

_logger = logging.getLogger(__name__)


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    def _post_load_demo_data(self, company=False):
        if company and company.account_fiscal_country_id.code == 'IN':
            self._update_l10n_in_demo_data(company)
        return super()._post_load_demo_data(company)

    @api.model
    def _update_l10n_in_demo_data(self, company=False):
        indian_companies = company or self.env['res.company'].search([('account_fiscal_country_id.code', '=', 'IN')])
        invoice_xmlids = [
            'demo_invoice_b2b_1',
            'demo_invoice_b2b_2',
            'demo_invoice_b2cs',
            'demo_invoice_b2cl',
            'demo_invoice_nill',
        ]
        default_ewaybill_vals = {
            'distance': 20,
            'type_id': self.env.ref("l10n_in_ewaybill.type_tax_invoice_sub_type_supply").id,
            'mode': "1",
            'vehicle_no': "GJ11AA1234",
            'vehicle_type': "R",
        }
        for indian_company in indian_companies:
            if indian_company.state_id:
                invoice_ids = []
                for inv_xmlid in invoice_xmlids:
                    invoice = self.with_company(indian_company).ref(inv_xmlid)
                    if invoice and not invoice.l10n_in_ewaybill_ids:
                        invoice_ids.append(invoice)

                if invoice_ids:
                    self.env['l10n.in.ewaybill'].create([{
                        **default_ewaybill_vals,
                        'account_move_id': invoice.id,
                    } for invoice in invoice_ids])
            else:
                _logger.error('Error while loading Indian-Ewaybill demo data in the company "%s".State is not set in the company.', indian_company.name)
