# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from stdnum import luhn


class AccountMove(models.Model):
    _inherit = "account.move"

    def _get_invoice_reference_no_invoice(self):
        """ This computes the reference based on the Odoo format.
            We calculat reference using invoice number and
            partner id and added control digit at last.
        """
        return self._get_kid_number()

    def _get_invoice_reference_no_partner(self):
        """ This computes the reference based on the Odoo format.
            We calculat reference using invoice number and
            partner id and added control digit at last.
        """
        return self._get_kid_number()

    def _get_kid_number(self):
        self.ensure_one()
        invoice_name = ''.join([i for i in self.name if i.isdigit()]).zfill(7)
        ref = (str(self.partner_id.id).zfill(7)[-7:] + invoice_name[-7:])
        return ref + luhn.calc_check_digit(ref)
