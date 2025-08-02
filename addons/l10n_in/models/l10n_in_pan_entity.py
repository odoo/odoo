from stdnum.in_ import pan
from odoo import api, fields, models


class L10nInPanEntity(models.Model):
    _name = 'l10n_in.pan.entity'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Indian PAN Entity'

    name = fields.Char(string="Number", tracking=1)
    type = fields.Selection([
        ('a', 'Association of Persons'),
        ('b', 'Body of Individuals'),
        ('c', 'Company'),
        ('f', 'Firms'),
        ('g', 'Government'),
        ('h', 'Hindu Undivided Family'),
        ('j', 'Artificial Judicial Person'),
        ('l', 'Local Authority'),
        ('p', 'Individual'),
        ('t', 'Association of Persons for a Trust'),
        ('k', 'Krish (Trust Krish)'),
    ], compute='_compute_type', readonly=True, store=True)
    partner_ids = fields.One2many(
        comodel_name='res.partner',
        inverse_name='l10n_in_pan_entity_id',
        string="Partners",
        domain="[('l10n_in_pan_entity_id', '=', False)]"
    )
    tds_deduction = fields.Selection([
        ('normal', 'Normal'),
        ('lower', 'Lower'),
        ('higher', 'Higher'),
        ('no', 'No'),
    ], string="TDS Deduction", default='normal', tracking=2)
    invalid = fields.Boolean(compute='_compute_invalid')

    _name_uniq = models.Constraint(
        'unique (name)',
        'A PAN Entity with same PAN Number already exists.',
    )

    @api.depends('name')
    def _compute_invalid(self):
        for record in self:
            if record.name and not pan.is_valid(record.name):
                record.invalid = True
            else:
                record.invalid = False

    @api.depends('name')
    def _compute_type(self):
        for record in self:
            if record.name:
                record.name = record.name.upper()
                if not record.invalid:
                    record.type = record.name[3].lower()
                else:
                    record.type = False
