# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class WizardPrice(models.Model):
    _name = "wizard.price"
    _description = "Compute Price Wizard"

    def _default_cost_price(self):
        template_id = self.env.context.get('active_id')
        assert template_id, _('Active ID is not set in Context.')
        product_template = self.env['product.template'].browse(template_id)
        computed_price = product_template.with_context(no_update=True).compute_standard_price()
        if product_template.id in computed_price:
            return "%s: %s" % (product_template.name, computed_price[product_template.id])
        return ""

    info_field = fields.Text(string="Info", readonly=True, default=_default_cost_price)
    real_time_accounting = fields.Boolean("Generate accounting entries when real-time")
    recursive = fields.Boolean("Change prices of child BoMs too")


    @api.multi
    def compute_from_bom(self):
        self.ensure_one()
        model = self.env.context.get('active_model')
        if model != 'product.template':
            raise UserError(_('This wizard is built for product templates, while you are currently running it from a product variant.'))
        template_id = self.env.context.get('active_id')
        assert template_id, _('Active ID is not set in Context.')
        product_template = self.env[model].browse(template_id)
        product_template.with_context(no_update=False).compute_standard_price(recursive=self.recursive, real_time_accounting=self.real_time_accounting)
