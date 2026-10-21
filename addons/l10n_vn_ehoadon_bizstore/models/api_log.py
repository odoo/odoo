# -*- coding: utf-8 -*-
import json

from odoo import fields, models


class EhoadonInvoiceLog(models.Model):
    _name = 'ehoadon.invoice.log'
    _description = 'eHoaDon API Log'
    _order = 'date desc, id desc'

    move_id = fields.Many2one(
        'account.move',
        string='Invoice',
        required=True,
        ondelete='cascade',
        index=True,
    )
    date = fields.Datetime(
        string='Date',
        default=fields.Datetime.now,
        required=True,
    )
    operation = fields.Selection(
        selection=[
            ('send', 'Send Invoice'),
            ('create_draft', 'Create Draft Invoice'),
            ('update', 'Update Draft'),
            ('delete', 'Delete Draft'),
            ('status', 'Refresh Status'),
            ('error_inform', 'Send Error Inform'),
            ('preview', 'Preview Invoice'),
            ('download_pdf', 'Download PDF'),
            ('download_xml', 'Download XML'),
            ('token', 'Get Token'),
        ],
        string='Operation',
        required=True,
    )
    status = fields.Selection(
        selection=[
            ('success', 'Success'),
            ('error', 'Error'),
        ],
        string='Status',
        required=True,
    )
    message = fields.Text(string='Message')
    payload = fields.Text(string='Payload')

    def set_payload_from_dict(self, payload):
        self.ensure_one()
        if payload is None:
            self.payload = False
            return
        try:
            self.payload = json.dumps(payload, ensure_ascii=False, indent=2)
        except TypeError:
            self.payload = str(payload)
