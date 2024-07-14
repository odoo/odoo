# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re

from odoo import api, models, fields, _
from odoo.exceptions import ValidationError


class L10nChLocationUnit(models.Model):
    _inherit = "l10n.ch.location.unit"

    weekly_hours = fields.Float(string="Weekly Hours")
    weekly_lessons = fields.Float(string="Weekly Lessons")

    @api.constrains('bur_ree_number')
    def _check_bur_ree_number(self):
        pattern = r'[A-Z][0-9]{8}'
        for location in self:
            if location.bur_ree_number:
                if re.fullmatch(pattern, location.bur_ree_number):
                    if not self.env['res.company']._l10n_ch_modulo_11_checksum(location.bur_ree_number, 7):
                        raise ValidationError(_("BUR-REE-Number checksum is not correct"))
                else:
                    raise ValidationError(_("BUR-REE-Number does not match the right format"))
