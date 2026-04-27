# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, models, fields
from odoo.exceptions import ValidationError


class L10nChHrEmployeeChildren(models.Model):
    _inherit = 'l10n.ch.hr.employee.children'

    last_name = fields.Char("Last Name")
    sex = fields.Selection(selection=[('M', 'Male'), ('F', 'Female')])
    birthdate = fields.Date(required=False)
    l10n_ch_sv_as_number = fields.Char(required=False, string="SV-AS Number")
    deduction_start = fields.Date(required=False)
    deduction_end = fields.Date(required=False)

    """
    @api.constrains('birthdate')
    def _check_birthdate(self):
        for child in self:
            if child.birthdate and child.birthdate > fields.Datetime.today().date():
                raise ValidationError(_('Birth date cannot be greater than today'))
    """
    @api.constrains('deduction_end')
    def _check_deduction_end(self):
        for child in self:
            if child.deduction_end and child.deduction_end < child.deduction_start:
                raise ValidationError(_('End of deduction period cannot be before the starting period'))

    @api.constrains('l10n_ch_sv_as_number')
    def _check_l10n_ch_sv_as_number(self):
        """
        SV-AS number is encoded using EAN13 Standard Checksum control
        """
        for child in self:
            if not child.l10n_ch_sv_as_number:
                continue
            self.env['hr.employee']._validate_sv_as_number(child.l10n_ch_sv_as_number)
