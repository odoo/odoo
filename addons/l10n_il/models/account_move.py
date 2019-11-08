# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class AccountMove(models.Model):
    _inherit = 'account.move'

    is_original_printed = fields.Boolean(
        default=False,
        help="Technical field used to display 'Original' on first pdf print")

    def consume_original_print(self):
        """
        Inform if original pdf has been printed and mark it as printed if it wasn't already the case.
        Only a posted invoice can consume the original print

        :return: True the first time, False otherwise
        """
        if self.state != 'posted' or self.is_original_printed:
            return False
        self.is_original_printed = True
        return True
