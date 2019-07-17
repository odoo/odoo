# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (c) 2011 Noviat nv/sa (www.noviat.be). All rights reserved.

import random
import re

from odoo import api, fields, models, _
from odoo.exceptions import UserError

"""
account.move object: add support for Belgian structured communication
"""


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _get_reference_be_partner(self):
        """ This computes the reference based on the belgian national standard
            “OGM-VCS”.
            For instance, if an invoice is issued for the partner with internal
            reference 'food buyer 654', the digits will be extracted and used as
            the data. This will lead to a check number equal to 72 and the
            reference will be '+++000/0000/65472+++'.
            If no reference is set for the partner, its id in the database will
            be used.
        """
        self.ensure_one()
        bbacomm = (re.sub('\D', '', self.partner_id.ref or '') or str(self.partner_id.id))[-10:].rjust(10, '0')
        base = int(bbacomm)
        mod = base % 97 or 97
        reference = '+++%s/%s/%s%02d+++' % (bbacomm[:3], bbacomm[3:7], bbacomm[7:], mod)
        return reference

    def _get_reference_be_invoice(self):
        """ This computes the reference based on the belgian national standard
            “OGM-VCS”.
            The data of the reference is the database id number of the invoice.
            For instance, if an invoice is issued with id 654, the check number
            is 72 so the reference will be '+++000/0000/65472+++'.
        """
        self.ensure_one()
        base = self.id
        bbacomm = str(base).rjust(10, '0')
        base = int(bbacomm)
        mod = base % 97 or 97
        reference = '+++%s/%s/%s%02d+++' % (bbacomm[:3], bbacomm[3:7], bbacomm[7:], mod)
        return reference
