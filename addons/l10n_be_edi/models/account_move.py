# -*- coding: utf-8 -*-

from odoo import models

import re

class AccountMove(models.Model):
    _inherit = 'account.move'

    def _get_ubl_values(self):
        values = super(AccountMove, self)._get_ubl_values()

        # E-fff uses ubl_version 2.0, account_edi_ubl supports ubl_version 2.1 but generates 2.0 UBL
        # so we only need to override the version to be compatible with E-FFF
        values['ubl_version'] = 2.0

        return values

    def _get_efff_name(self):
        self.ensure_one()
        vat = self.company_id.partner_id.commercial_partner_id.vat
        return 'efff_%s%s%s' % (vat or '', '_' if vat else '', re.sub('[\W_]', '', self.name))  # official naming convention
