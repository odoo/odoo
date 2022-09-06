# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class AccountMove(models.Model):
    _inherit = 'account.move'

    ####################################################
    # Import Electronic Document
    ####################################################

    def _get_create_document_from_attachment_decoders(self):
        # Override account
        res = super()._get_create_document_from_attachment_decoders()
        res.append((5, self.env['account.facturx']._facturx_create_document_from_attachment))
        return res

    def _get_update_invoice_from_attachment_decoders(self, invoice):
        # Override account
        res = super()._get_update_invoice_from_attachment_decoders(invoice)
        res.append((5, self.env['account.facturx']._facturx_update_invoice_from_attachment))
        return res
