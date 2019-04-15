# coding: utf-8
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class PosConfig(models.Model):
    _inherit = 'pos.config'

    handle_tip_adjustments = fields.Boolean('Handle Tip Adjustments')
    print_tip_on_receipt = fields.Boolean('Print Tip On Receipt')

    @api.constrains('handle_tip_adjustments', 'tip_product_id')
    def _check_company_invoice_journal(self):
        if self.handle_tip_adjustments and not self.tip_product_id:
            raise ValidationError(_("To handle tip adjustments please configure a Tip Product."))
