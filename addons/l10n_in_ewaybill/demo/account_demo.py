import logging
from odoo import models
from odoo.addons.account.models.chart_template import template

_logger = logging.getLogger(__name__)


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('in', model='res.company', demo=True)
    def _l10n_in_ewaybill_res_company_demo(self):
        return {
            self.env.company.id: {
                'l10n_in_ewaybill_feature': True,
                'l10n_in_ewaybill_username': 'iap_odoo',
                'l10n_in_ewaybill_password': 'odoo',
            },
        }

    @template(template='in', model='l10n.in.ewaybill', demo=True)
    def _l10n_in_ewaybill_demo(self):
        if not self.env.company.state_id:
            return {}
        invoices = [
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
        return {
            f'ewaybill_{invoice}': {
                **default_ewaybill_vals,
                'account_move_id': invoice,
                'company_id': self.env.company.id,
            }
            for invoice in invoices
        }
