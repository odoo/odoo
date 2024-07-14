# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError

import re

uid_bfs_pattern = r'CHE-[0-9]{3}\.[0-9]{3}\.[0-9]{3}'


class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_ch_post_box = fields.Char(string="Post Box")
    l10n_ch_uid = fields.Char(string="Identification Number (IDE-OFS)")

    @api.model
    def _l10n_ch_modulo_11_checksum(self, string, control_number_index):
        multipliers = [5, 4, 3, 2, 7, 6, 5, 4]
        digits = [int(char) for char in string if char.isdigit()]
        result = sum(digit * multiplier for digit, multiplier in zip(digits[:control_number_index], multipliers))
        checksum_result = 11 - (result % 11)

        return digits[-1] == checksum_result

    @api.constrains('l10n_ch_uid')
    def _check_l10n_ch_uid(self):
        """
        Identification Number (IDE-OFS) must be either empty or have the right format and respect
        the modulo 11 checksum.
        """
        for company in self:
            if company.l10n_ch_uid:
                if re.fullmatch(uid_bfs_pattern, company.l10n_ch_uid):
                    if not self._l10n_ch_modulo_11_checksum(company.l10n_ch_uid, 8):
                        raise ValidationError(_("Identification Number (IDE-OFS) checksum is not correct"))
                else:
                    raise ValidationError(_("Identification Number (IDE-OFS) does not match the right format"))
