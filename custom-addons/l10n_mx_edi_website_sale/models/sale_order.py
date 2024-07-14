# coding: utf-8

from odoo import models, api


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.depends('website_id')
    def _compute_l10n_mx_edi_cfdi_to_public(self):
        # Extends 'l10n_mx_edi_sale'
        # when creating a sale order from the website, the default 'l10n_mx_edi_cfdi_to_public' should be true
        super()._compute_l10n_mx_edi_cfdi_to_public()
        for order in self:
            if order.website_id and order.company_id.country_code == 'MX':
                order.l10n_mx_edi_cfdi_to_public = True
