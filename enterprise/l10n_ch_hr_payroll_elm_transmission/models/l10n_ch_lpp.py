# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, models, fields
from odoo.exceptions import ValidationError

import re
uid_bfs_pattern = r'CHE-[0-9]{3}\.[0-9]{3}\.[0-9]{3}'


class l10nChLppInsurance(models.Model):
    _inherit = 'l10n.ch.lpp.insurance'

    insurance_company = fields.Char(required=False)
    company_id = fields.Many2one("res.company", default=lambda self: self.env.company)
    uid_bfs = fields.Char(string="UID-BFS")
    solutions_ids = fields.One2many('l10n.ch.lpp.insurance.line', 'institution_id')
    active = fields.Boolean(default=True)

    @api.constrains('uid_bfs')
    def _check_uid_bfs(self):
        """
        Identification Number (UID-BFS) must be either empty or have the right format and respect
        the modulo 11 checksum.
        """
        for record in self:
            if record.uid_bfs:
                if re.fullmatch(uid_bfs_pattern, record.uid_bfs):
                    if not self.env['res.company']._l10n_ch_modulo_11_checksum(record.uid_bfs, 8):
                        raise ValidationError(_("Identification Number (IDE-OFS) checksum is not correct"))
                else:
                    raise ValidationError(_("Identification Number (IDE-OFS) does not match the right format"))

class l10nChLppInsuranceSolution(models.Model):
    _name = 'l10n.ch.lpp.insurance.line'
    _description = 'LPP Solutions'

    institution_id = fields.Many2one('l10n.ch.lpp.insurance')
    name = fields.Char(required=True)
    code = fields.Char(required=True)

    @api.constrains('code')
    def _check_code(self):
        """
        Identification Number (UID-BFS) must be either empty or have the right format and respect
        the modulo 11 checksum.
        """
        for record in self:
            if record.code:
                if len(record.code) > 8:
                    raise ValidationError(_("Identification Number (IDE-OFS) checksum is not correct"))
