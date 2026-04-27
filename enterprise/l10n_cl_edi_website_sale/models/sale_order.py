from odoo import models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def _prepare_invoice(self):
        # EXTENDS sale_order
        values = super()._prepare_invoice()
        if self.website_id and self.website_id.company_id.account_fiscal_country_id.code == 'CL' \
                and self.partner_invoice_id.id == self.env.ref('l10n_cl.par_cfa').id:
            values['l10n_latam_document_type_id'] = self.env.ref('l10n_cl.dc_b_f_dte').id
        return values
