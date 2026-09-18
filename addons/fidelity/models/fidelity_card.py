from uuid import uuid4

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class FidelityCard(models.Model):
    """
    `fidelity.card`, formerly `loyalty.card`, works a little differently.
    Each partner will now have a single `fidelity.card` to which multiple
    programs can add points via `transaction_ids`.

    Transactions will be used to calculate the number of points
    used/added per program.

    This way, customers will only have to present one card for the
    entire fidelity program.

    This model is not company-specific, as fidelity cards can be
    used across multiple companies within a multi-company environment.
    """
    _name = 'fidelity.card'
    _description = "Fidelity Card"
    _rec_name = 'code'

    active = fields.Boolean(default=True)
    code = fields.Char(required=True, default=lambda self: "044" + str(uuid4())[7:-18])
    partner_id = fields.Many2one('res.partner', index=True)
    partner_image_1920 = fields.Image(related='partner_id.image_1920', string="Partner Image", readonly=True)
    balance_ids = fields.One2many('fidelity.balance', 'card_id')
    program_ids = fields.Many2many('fidelity.program', compute='_compute_program_ids', readonly=True)
    nb_programs = fields.Integer(string="Programs", compute='_compute_program_ids', readonly=True)

    _card_code_unique = models.Constraint(
        'UNIQUE(code)',
        "A fidelity card must have a unique code.",
    )

    @api.depends('balance_ids', 'balance_ids.program_id')
    def _compute_program_ids(self):
        for card in self:
            programs = card.balance_ids.mapped('program_id')
            card.program_ids = programs
            card.nb_programs = len(programs)

    @api.constrains('active', 'partner_id')
    def _check_single_loyalty_card_per_partner(self):
        for card in self:
            loyalty_card_count = self.search_count([
                ('id', '!=', card.id),
                ('partner_id', '=', card.partner_id.id),
            ], limit=1)
            if loyalty_card_count:
                raise ValidationError(self.env._(
                    "A customer can only have one active loyalty card per program.",
                ))
