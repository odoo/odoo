from odoo import fields, models
from odoo.fields import Domain


class WebsiteCheckoutStep(models.Model):
    _name = "website.checkout.step"
    _description = "Website Checkout Step"
    _inherit = ["mixin.website.published.multi"]

    name = fields.Char(
        translate=True,
        required=True,
    )
    sequence = fields.Integer()
    step_href = fields.Char(
        string="Href",
        required=True,
    )
    main_button_label = fields.Char(translate=True)
    back_button_label = fields.Char(translate=True)
    website_id = fields.Many2one(
        comodel_name="website",
        ondelete="cascade",
    )

    def _get_next_checkout_step(self, allowed_steps_domain):

        next_step_domain = Domain.AND(
            [allowed_steps_domain, [("sequence", ">", self.sequence)]]
        )
        return self.search(next_step_domain, order="sequence", limit=1)

    def _get_previous_checkout_step(self, allowed_steps_domain):

        previous_step_domain = Domain.AND(
            [allowed_steps_domain, [("sequence", "<", self.sequence)]]
        )
        return self.search(previous_step_domain, order="sequence DESC", limit=1)
