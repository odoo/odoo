# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields


class L10nLatamDocumentType(models.Model):

    _inherit = 'l10n_latam.document.type'

    internal_type = fields.Selection(
        selection_add=[
            ('invoice', 'Invoices'),
            ('invoice_in', 'Purchase Invoices'),
            ('debit_note', 'Debit Notes'),
            ('credit_note', 'Credit Notes'),
            ('receipt_invoice', 'Receipt Invoice')])

    def _get_document_sequence_vals(self, journal):
        values = super(L10nLatamDocumentType, self)._get_document_sequence_vals(journal)
        if self.country_id != self.env.ref('base.cl'):
            return values
        values.update({
            'padding': 6,
            'implementation': 'no_gap',
            'l10n_latam_document_type_id': self.id,
            'prefix': None
        })
        return values

    def _filter_taxes_included(self, taxes):
        """ In Chile we include taxes in line amounts depending on type of document.
        This serves just for document printing purposes """
        self.ensure_one()
        if self.country_id == self.env.ref('base.cl') and self.code in ['39', '41', '110', '111', '112', '34']:
            return taxes.filtered(lambda x: x.tax_group_id == self.env.ref('l10n_cl.tax_group_iva_19'))
        return super()._filter_taxes_included(taxes)
