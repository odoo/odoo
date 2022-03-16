# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.tests.common import TransactionCase

import base64


class EdiTestCommon(TransactionCase):

    @classmethod
    def EDISetUpClass(cls, edi_format_ref=None):
        """Does not use setUpClass, as we will want to use this in a variety of scenario where other common parents
        are already used (e.g. accounting tests)"""
        #todo maybe there is a better way
        if edi_format_ref:
            cls.edi_format = cls.env.ref(edi_format_ref)
        else:
            cls.edi_format = cls.env['edi.format'].sudo().create({
                'name': 'Test EDI format',
                'code': 'test_edi',
            })

    ####################################################
    # EDI helpers
    ####################################################

    def create_edi_flow(self, edi_format=None, document=None, flow_type='send'):
        """ Creates a flow based on an existing invoice or creates one, too.

        :param edi_format:  The edi_format of the document.
        :param document:    The document (object) to which we wish to link this flow.
        :param flow_type:   The type of this flow (send or cancel)
        """
        return self.env['edi.flow'].create({
            'edi_format_id': (edi_format or self.edi_format).id,
            'res_id': (document or self.document).id,
            'res_model': (document or self.document)._name,
            'state': 'to_send',
            'flow_type': flow_type
        })

    def _mock_get_edi_format_settings_return(self, batching_key='batch', needs_web_services=True, mocked_cancel_method=None, mocked_send_method=None):
        return {
            'needs_web_services': needs_web_services,
            'attachments_required_in_mail': True,
            'document_needs_embedding': True,
            'batching_key': batching_key,
            'stages': {
                'send': {
                    'Initialized': {
                        'new_state': 'to_send',
                        'action': mocked_send_method or self._mocked_send
                    },
                    'XML File Created': {
                        'new_state': 'sent',
                    },
                },
                'cancel': {
                    'Initialized': {
                        'new_state': 'to_cancel',
                        'action': mocked_cancel_method or self._mocked_cancel_success
                    },
                    'Cancelled': {
                        'new_state': 'cancelled',
                    },
                },
            }
        }

    def _mocked_send(self, flows):
        res = {}
        documents = flows._get_documents()
        for flow in flows:
            for document in documents.filtered(lambda d: d.id == flow.res_id):
                attachment = flow.env['ir.attachment'].create({
                    'name': 'mock_simple.xml',
                    'datas': base64.encodebytes(b"<?xml version='1.0' encoding='UTF-8'?><Invoice/>"),
                    'mimetype': 'application/xml'
                })
                self.env['edi.file'].create({
                    'edi_flow_id': flow.id,
                    'attachment_id': attachment.id,
                    'code': 'test',
                })
                res[document.id] = {'success': True, 'attachment': attachment}
        return res

    def _mocked_cancel_success(self, flows):
        return {document.id: {'success': True} for document in flows._get_documents()}
