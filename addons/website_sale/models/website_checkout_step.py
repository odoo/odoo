# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.fields import Domain


class WebsiteCheckoutStep(models.Model):
    _name = 'website.checkout.step'
    _description = 'Website Checkout Step'
    _inherit = ['website.published.multi.mixin']

    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer()
    step_href = fields.Char(string="Href", required=True)
    main_button_label = fields.Char(translate=True)
    back_button_label = fields.Char(translate=True)
    website_id = fields.Many2one('website', ondelete='cascade')

    def _get_next_checkout_step(self, allowed_steps_domain):
        """ Get the next step in the checkout flow based on the sequence."""

        next_step_domain = Domain.AND(
            [allowed_steps_domain, [('sequence', '>', self.sequence)]]
        )
        return self.search(next_step_domain, order='sequence', limit=1)

    def _get_previous_checkout_step(self, allowed_steps_domain):
        """ Get the previous step in the checkout flow based on the sequence."""

        previous_step_domain = Domain.AND(
            [allowed_steps_domain, [('sequence', '<', self.sequence)]]
        )
        return self.search(previous_step_domain, order='sequence DESC', limit=1)
