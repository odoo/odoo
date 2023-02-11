# -*- coding: utf-8 -*-

from odoo import models

import re


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _get_efff_name(self):
        self.ensure_one()
        vat = self.company_id.partner_id.commercial_partner_id.vat
        return 'efff_%s%s%s' % (vat or '', '_' if vat else '', re.sub(r'[\W_]', '', self.name))  # official naming convention
