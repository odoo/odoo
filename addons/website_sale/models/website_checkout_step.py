# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class WebsiteCheckoutStep(models.Model):
    _name = 'website.checkout.step'
    _description = 'Website Checkout Step'
    _inherit = ['website.published.multi.mixin']

    # TODO-PDA which ones required?
    name = fields.Char(required=True, translate=True)
    xmlid = fields.Char()
    # TODO-PDA drag and drop to define the sequence?
    sequence = fields.Integer()

    current_href = fields.Char()

    # TODO-PDA all those fields are dependent of the next step or previous step, to be computed based on current_href or xmlid
    main_button = fields.Char(translate=True)
    main_button_href = fields.Char()
    back_button = fields.Char(translate=True)
    back_button_href = fields.Char()

    @api.model
    def get_checkout_steps(self, website_id=None):
        website_id = website_id or self.env.context.get('website_id')
        domain = ['|',('website_id', '=', website_id), ('website_id', '=', False), ('is_published', '=', True)]
        return self.search(domain, order='sequence')
