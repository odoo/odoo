# -*- coding: utf-8 -*-
"""
@author: Online ERP Hungary Kft.
"""

from odoo import fields, models, api


class AccountFiscalPosition(models.Model):
    _inherit = "account.fiscal.position"

    @api.model
    def map_tax(self, taxes):
        product = self.env.context.get("l10n_hu_product_id")

        if not product:
            return super(AccountFiscalPosition, self).map_tax(taxes)

        if not self:
            return taxes
        result = self.env["account.tax"]
        for tax in taxes:
            taxes_correspondance = self.tax_ids.filtered(lambda t: t.tax_src_id == tax._origin)
            ############ FROM HERE ############
            # Take into account the type of product
            if (
                product
                and taxes_correspondance
                and product.detailed_type == "service"
                and taxes_correspondance.service_tax_dest_id
            ):
                result |= taxes_correspondance.service_tax_dest_id
            else:
                result |= taxes_correspondance.tax_dest_id if taxes_correspondance else tax
            ############ TO HERE ############
        return result


class AccountFiscalPositionTaxDivided(models.Model):
    _inherit = "account.fiscal.position.tax"

    service_tax_dest_id = fields.Many2one("account.tax", string="Tax to Apply if Service")


class AccountFiscalPositionTaxDividedTemplate(models.Model):
    _inherit = "account.fiscal.position.tax.template"

    service_tax_dest_id = fields.Many2one("account.tax.template", string="Tax to Apply if Service")
