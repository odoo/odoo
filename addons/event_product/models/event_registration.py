from odoo import api, fields, models
from odoo.exceptions import ValidationError


class EventRegistration(models.Model):
    _inherit = 'event.registration'

    sale_status = fields.Selection(string="Sale Status", selection=[
            ('to_pay', 'Not Sold'),
            ('sold', 'Sold'),
            ('free', 'Free'),
        ], compute="_compute_registration_status", compute_sudo=True, store=True, readonly=True, precompute=True)

    ticket_option_product_ids = fields.Many2many(
        'product.product', 'event_registration_ticket_option_rel', 'registration_id', 'product_id',
        string='Optional Products', copy=False,
        help="Optional products of the ticket chosen by this attendee.")
    ticket_optional_product_ids = fields.Many2many(
        related='event_ticket_id.optional_product_ids', string='Available Optional Products')

    @api.constrains('event_ticket_id', 'ticket_option_product_ids')
    def _check_ticket_option_product_ids(self):
        for registration in self:
            invalid = registration.ticket_option_product_ids - registration.event_ticket_id.optional_product_ids
            if invalid:
                raise ValidationError(self.env._(
                    "%(options)s: not an option of ticket \"%(ticket)s\".",
                    options=invalid.mapped('display_name'),
                    ticket=registration.event_ticket_id.name or self.env._("(no ticket)"),
                ))

    @api.onchange('event_ticket_id')
    def _onchange_event_ticket_id_ticket_options(self):
        """ Drop the options the new ticket does not offer: the checkboxes only hide them. """
        for registration in self:
            registration.ticket_option_product_ids &= registration.event_ticket_id.optional_product_ids

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
