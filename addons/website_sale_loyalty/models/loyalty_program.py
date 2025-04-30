# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class LoyaltyProgram(models.Model):
    _name = 'loyalty.program'
    _inherit = ['loyalty.program', 'website.multi.mixin']

    ecommerce_ok = fields.Boolean("Available on Website", default=True)
    show_non_published_product_warning = fields.Boolean(compute='_compute_show_non_published_product_warning')

    @api.depends('program_type', 'trigger_product_ids.website_published')
    def _compute_show_non_published_product_warning(self):
        for program in self:
            program.show_non_published_product_warning = (
                program.program_type == 'ewallet'
                and any(not product.website_published for product in program.trigger_product_ids)
            )

    def action_program_share(self):
        self.ensure_one()
        return self.env['coupon.share'].create_share_action(program=self)
