from odoo import fields, models


class EventRegistration(models.Model):
    _inherit = 'event.registration'

    sale_status = fields.Selection(string="Sale Status", selection=[
            ('to_pay', 'Not Sold'),
            ('sold', 'Sold'),
            ('free', 'Free'),
        ], compute="_compute_registration_status", compute_sudo=True, store=True, readonly=True, precompute=True)

    def _has_order(self):
        return False

    # sale_status can be computed in pos_event and event_sale. We need to make it
    # available in both modules, so its now in event module.
    def _compute_registration_status(self):
        if not self._has_order():
            for reg in self:
                if not reg.sale_status:
                    reg.sale_status = 'free'
                if not reg.state:
                    reg.state = 'open'
