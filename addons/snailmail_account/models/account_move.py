# -*- coding: utf-8 -*-
from odoo.addons import account
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class AccountMove(models.Model, account.AccountMove):

    def _get_pdf_and_send_invoice_vals(self, template, **kwargs):
        # EXTENDS account
        vals = super()._get_pdf_and_send_invoice_vals(template, **kwargs)
        vals['checkbox_send_by_post'] = False
        return vals
