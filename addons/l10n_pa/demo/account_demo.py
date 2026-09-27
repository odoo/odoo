# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template(model='account.move', demo=True)
    def _get_demo_data_move(self, template_code):
        move_data = super()._get_demo_data_move(template_code)
        if template_code == 'pa':
            # vendor documents are numbered by the vendor, the number has to be given manually
            move_data[self.company_xmlid('demo_invoice_8')]['l10n_latam_document_number'] = '0000000001'
            move_data[self.company_xmlid('demo_invoice_equipment_purchase')]['l10n_latam_document_number'] = '0000000002'
            move_data[self.company_xmlid('demo_move_auto_reconcile_3')]['l10n_latam_document_number'] = '0000000003'
        return move_data

    def _post_load_demo_data(self, chart_template):
        super()._post_load_demo_data(chart_template)
        if chart_template != 'pa':
            return
        for partner_xmlid, fiscal_position_xmlid in (
            ('l10n_pa.partner_pa_demo_4', 'fp_foreign'),
            ('l10n_pa.partner_pa_demo_5', 'fp_zona_franca'),
        ):
            partner = self.env.ref(partner_xmlid, raise_if_not_found=False)
            fiscal_position = self.ref(fiscal_position_xmlid, raise_if_not_found=False)
            if partner and fiscal_position:
                partner.property_account_position_id = fiscal_position
