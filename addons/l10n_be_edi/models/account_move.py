# -*- coding: utf-8 -*-

from odoo import models


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _get_ubl_values(self):
        values = super(AccountMove, self)._get_ubl_values()

        # E-fff uses ubl_version 2.0, account_edi_ubl supports ubl_version 2.1 but generates 2.0 UBL
        # so we only need to override the version to be compatible with E-FFF
        values['ubl_version'] = 2.0

        return values
