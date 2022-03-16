# -*- coding: utf-8 -*-

from odoo import models

import markupsafe


class EdiFormat(models.Model):
    _inherit = 'edi.format'

    def _get_edi_format_settings(self, document=None, stage=None, flow_type=None):
        self.ensure_one()
        if self.code != 'efff_1':
            return super()._get_edi_format_settings(document, stage, flow_type)
        return {
            'needs_web_services': False,
            'attachments_required_in_mail': False,
            'document_needs_embedding': document and document.is_sale_document() and document.state != 'draft',
            'stages': {
                'send': {
                    'Initialized': {
                        'new_state': 'to_send',
                        'action': self._create_efff_attachment,
                    },
                    'XML File Created': {
                        'new_state': 'sent',
                        'make_attachments_official': True,
                    },
                }
            }
        }

    ####################################################
    # Export
    ####################################################

    def _get_efff_values(self, invoice):
        return {
            **self._get_ubl_values(invoice),
            'ubl_version': 2.0,
        }

    def _export_efff(self, invoice):
        self.ensure_one()
        # Create file content.
        xml_content = markupsafe.Markup("<?xml version='1.0' encoding='UTF-8'?>")
        xml_content += self.env['ir.qweb']._render('l10n_be_edi.export_efff_invoice', self._get_efff_values(invoice))
        xml_name = '%s.xml' % invoice._get_efff_name()
        return {
            'name': xml_name,
            'raw': xml_content.encode(),
            'mimetype': 'application/xml',
            'code': 'xml'
        }

    ####################################################
    # Account.edi.format override
    ####################################################

    def _import_document_from_xml_tree(self, filename, tree):
        self.ensure_one()
        if self.code == 'efff_1' and self._is_ubl(filename, tree):
            return self._create_invoice_from_ubl(tree)
        return super()._import_document_from_xml_tree(filename, tree)

    def _update_document_from_xml_tree(self, filename, tree, invoice):
        self.ensure_one()
        if self.code == 'efff_1' and self._is_ubl(filename, tree):
            return self._update_invoice_from_ubl(tree, invoice)
        return super()._update_document_from_xml_tree(filename, tree, invoice)

    def _is_format_applicable(self, journal):
        self.ensure_one()
        if self.code != 'efff_1':
            return super()._is_format_applicable(journal)
        return journal.type == 'sale' and journal.country_code == 'BE'

    def _create_efff_attachment(self, flows):
        self.ensure_one()
        if self.code != 'efff_1':
            return
        # We just posted the moves, so we can generate the attachments
        res = {}
        moves = flows._get_documents()
        for flow in flows:
            for invoice in moves.filtered(lambda m: m.id == flow.res_id):
                attachment_vals = self._export_efff(invoice)
                res[invoice.id] = {'success': True, 'attachment': flow._create_or_update_edi_files([attachment_vals])}
        return res

    def _is_format_required(self, document, document_type=''):
        self.ensure_one()
        if self.code != 'efff_1':
            return super()._is_format_required(document, document_type)
        return document_type in ('invoice', 'payment') and document.is_invoice(include_receipts=True)
