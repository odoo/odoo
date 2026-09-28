from odoo import models

from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template(model='account.move', demo=True)
    def _get_demo_data_move(self, template_code):
        move_data = super()._get_demo_data_move(template_code)
        if template_code == 'cr':
            # vendor documents are numbered by the vendor, the number has to be given manually
            move_data[self.company_xmlid('demo_invoice_8')]['l10n_latam_document_number'] = '0000000001'
            move_data[self.company_xmlid('demo_invoice_equipment_purchase')]['l10n_latam_document_number'] = '0000000002'
            move_data[self.company_xmlid('demo_move_auto_reconcile_3')]['l10n_latam_document_number'] = '0000000003'
        return move_data

    def _post_load_demo_data(self, chart_template):
        super()._post_load_demo_data(chart_template)
        if chart_template != 'cr':
            return
        partner = self.env.ref('l10n_cr.demo_partner_zona_franca', raise_if_not_found=False)
        fiscal_position = self.ref('fiscal_position_cr_zona_franca', raise_if_not_found=False)
        if partner and fiscal_position:
            partner.property_account_position_id = fiscal_position
