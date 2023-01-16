# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    @api.onchange('purchase_vendor_bill_id', 'purchase_id')
    def _onchange_purchase_auto_complete(self):
        purchase_order_id = self.purchase_vendor_bill_id.purchase_order_id or self.purchase_id
        if purchase_order_id and purchase_order_id.l10n_in_company_country_code == 'IN':
            journal_id = self.purchase_vendor_bill_id.purchase_order_id.l10n_in_journal_id or self.purchase_id.l10n_in_journal_id
            if journal_id:
                self.journal_id = journal_id
            self.l10n_in_gst_treatment = purchase_order_id.l10n_in_gst_treatment
        return super()._onchange_purchase_auto_complete()
