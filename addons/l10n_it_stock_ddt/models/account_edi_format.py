# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class AccountEdiFormat(models.Model):
    _inherit = 'account.edi.format'

    def _l10n_it_invoice_is_direct(self, invoice):
        """ An invoice is only direct if the Transport Documents are all done the same day as the invoice. """
        for ddt in invoice.l10n_it_ddt_ids:
            if not ddt.date_done or ddt.date_done.date() != invoice.invoice_date:
                return False
        return True

    def _l10n_it_get_invoice_features_for_document_type_selection(self, invoice):
        res = super()._l10n_it_get_invoice_features_for_document_type_selection(invoice)
        res['direct_invoice'] = self._l10n_it_invoice_is_direct(invoice)
        return res

    def _l10n_it_document_type_mapping(self):
        """ Deferred invoices (not direct) require TD24 FatturaPA Document Type. """
        res = super()._l10n_it_document_type_mapping()
        for document_type, infos in res.items():
            if document_type == 'TD07':
                continue
            infos['direct_invoice'] = True
        res['TD24'] = dict(move_types=['out_invoice'], import_type='in_invoice', direct_invoice=False)
        return res
