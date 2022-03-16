# -*- coding: utf-8 -*-

from odoo import models

import logging
import base64

_logger = logging.getLogger(__name__)


DEFAULT_FACTURX_DATE_FORMAT = '%Y%m%d'


class EdiFormat(models.Model):
    _inherit = 'edi.format'

    def _get_edi_format_settings(self, document=None, stage=None, flow_type=None):
        self.ensure_one()
        if self.code != 'edi_test':
            return super()._get_edi_format_settings(document, stage, flow_type=None)
        return {
            'needs_web_services': True,
            'attachments_required_in_mail': True,
            'document_needs_embedding': True,
            'batching_key': document and (document.ref,),
            'stages': {
                'send': {
                    'Initialized': {
                        'new_state': 'to_send',
                        'action': self._action_send
                    },
                    'XML File Created': {
                        'new_state': 'sent',
                    },
                },
                'cancel': {
                    'Initialized': {
                        'new_state': 'to_cancel',
                        'action': self._action_cancel
                    },
                    'Cancelled': {
                        'new_state': 'cancelled',
                    },
                },
            }
        }

    def _is_format_required(self, document, document_type=''):
        self.ensure_one()
        if self.code != 'edi_test':
            return super()._is_format_required(document, document_type)
        return document_type == 'res.partner' and not document.ref

    def _action_send(self, flows):
        res = {}
        documents = flows._get_documents()
        for flow in flows:
            for document in documents.filtered(lambda d: d.id == flow.res_id):
                attachment = flow.env['ir.attachment'].create({
                    'name': 'mock_simple.xml',
                    'datas': base64.encodebytes(b"<?xml version='1.0' encoding='UTF-8'?><Invoice/>"),
                    'mimetype': 'application/xml'
                })
                flow.env['edi.file'].create([{
                    'edi_flow_id': flow.id,
                    'attachment_id': attachment.id,
                    'code': 'test',
                }])
                res[document.id] = {'success': True, 'attachment': attachment}
        return res

    def _action_cancel(self, flows):
        return {document.id: {'success': True} for document in flows._get_documents()}
