# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from odoo.exceptions import UserError

import re
import string

uid_bfs_pattern = r'CHE-[0-9]{3}\.[0-9]{3}\.[0-9]{3}'


class l10nChAccidentInsurance(models.Model):
    _inherit = "l10n.ch.accident.insurance"

    @api.model
    def _get_default_laa_group_ids(self):
        vals = [
            (0, 0, {
                'name': "LAA Group A",
                'group_unit': "A",
            })
        ]
        return vals

    active = fields.Boolean(default=True)
    company_id = fields.Many2one("res.company", default=lambda self: self.env.company)
    insurance_company = fields.Char(required=False, store=True)
    uid_bfs_number = fields.Char(required=False)
    laa_group_ids = fields.One2many('l10n.ch.accident.group', 'insurance_id', default=_get_default_laa_group_ids)


    @api.constrains('uid_bfs_number')
    def _check_uid_bfs_number(self):
        """
        Identification Number (UID-BFS) must be either empty or have the right format and respect
        the modulo 11 checksum.
        """
        for record in self:
            if record.uid_bfs_number:
                if re.fullmatch(uid_bfs_pattern, record.uid_bfs_number):
                    if not self.env['res.company']._l10n_ch_modulo_11_checksum(record.uid_bfs_number, 8):
                        raise ValidationError(_("Identification Number (IDE-OFS) checksum is not correct"))
                else:
                    raise ValidationError(_("Identification Number (IDE-OFS) does not match the right format"))


class l10nChAccidentInsuranceGroup(models.Model):
    _name = "l10n.ch.accident.group"
    _description = "LAA Group category"

    @api.model
    def _get_default_laa_line_ids(self):
        vals = [
            (0, 0, {
                'date_from': fields.Date.today().replace(month=1, day=1),
                'threshold': 148200,
                'occupational_male_rate': 0,
                'non_occupational_male_rate': 0,
                'employer_aanp_part': '0',
            })
        ]
        return vals

    name = fields.Char()
    group_unit = fields.Selection(selection=[(char, char) for char in string.ascii_uppercase[string.ascii_uppercase.index('A'):]], required=True, string="Group Unit")
    insurance_id = fields.Many2one('l10n.ch.accident.insurance')
    line_ids = fields.One2many('l10n.ch.accident.insurance.line.rate', 'group_id', default=_get_default_laa_line_ids)

    def get_rates(self, target):
        self.ensure_one()
        for line in self.line_ids:
            if line.date_from <= target and (not line.date_to or target <= line.date_to):
                return line.threshold, line.occupational_male_rate, line.non_occupational_male_rate, int(line.employer_aanp_part or 0)
        raise UserError(_('No AAP/AANP threshold found for date %s', target))


class l10nChAccidentInsuranceLineRate(models.Model):
    _inherit = ['l10n.ch.accident.insurance.line.rate']

    group_id = fields.Many2one('l10n.ch.accident.group')
    employer_aanp_part = fields.Selection(selection=[('0', "0 %"),
                                                     ('50', "50 %")], default="0")
