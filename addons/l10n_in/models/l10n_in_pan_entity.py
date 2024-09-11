from stdnum.in_ import pan
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError, UserError


class L10nInPanEntity(models.Model):
    _name = "l10n_in.pan.entity"
    _description = 'Indian PAN Entity'

    name = fields.Char(string="PAN Number")
    partner_ids = fields.One2many('res.partner', 'l10n_in_pan_entity_id')
    pan_holder_type = fields.Char(compute="_compute_pan_holder_type", readonly=True)

    _sql_constraints = [
        ('pan_uniq', "unique(name)", "A PAN Entity with same PAN Number already exists.")
    ]

    @api.constrains('name')
    def _check_l10n_in_pan(self):
        for record in self:
            if record.name and not pan.is_valid(record.name):
                raise ValidationError(_('The entered PAN seems invalid. Please enter a valid PAN.'))

    @api.depends('name')
    def _compute_pan_holder_type(self):
        for record in self:
            if pan.is_valid(self.name):
                pan_info = pan.info(record.name)
                record.pan_holder_type = pan_info['holder_type']
            else:
                raise UserError(_('The entered PAN seems invalid. Please enter a valid PAN.'))
