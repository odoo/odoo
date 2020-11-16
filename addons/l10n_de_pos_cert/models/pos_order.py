# -*- coding: utf-8 -*-

from odoo import models, fields, api


class PosOrder(models.Model):
    _inherit = 'pos.order'

    fiskaly_transaction_uuid = fields.Char(string="Transaction ID", readonly=True, copy=False)
    fiskaly_transaction_number = fields.Integer(string="Transaction number", readonly=True, copy=False)
    fiskaly_time_start = fields.Char(string="Beginning", readonly=True, copy=False)
    fiskaly_time_end = fields.Char(string="End", readonly=True, copy=False)
    fiskaly_certificate_serial = fields.Char(string="Certificate serial", readonly=True, copy=False)
    fiskaly_timestamp_format = fields.Char(string="Timestamp format", readonly=True, copy=False)
    fiskaly_signature_value = fields.Char(string="Signature value", readonly=True, copy=False)
    fiskaly_signature_algorithm = fields.Char(string="Signature algo", readonly=True, copy=False)
    fiskaly_signature_public_key = fields.Char(string="Signature public key", readonly=True, copy=False)
    fiskaly_client_serial_number = fields.Char(string="Client serial", readonly=True, copy=False)

    @api.model
    def _order_fields(self, ui_order):
        fields = super(PosOrder, self)._order_fields(ui_order)
        if self.env.company.country_id == self.env.ref('base.de'):
            fields['fiskaly_transaction_uuid'] = ui_order['fiskaly_uuid']
            if 'tss_info' in ui_order:
                for key, value in ui_order['tss_info'].items():
                    fields['fiskaly_'+key] = value
        return fields

    def _export_for_ui(self, order):
        json = super(PosOrder, self)._export_for_ui(order)
        if self.env.company.country_id == self.env.ref('base.de'):
            tss_info = {
                'transaction_number': order.fiskaly_transaction_number,
                'time_start': order.fiskaly_time_start,
                'time_end': order.fiskaly_time_end,
                'certificate_serial': order.fiskaly_certificate_serial,
                'timestamp_format': order.fiskaly_timestamp_format,
                'signature_value': order.fiskaly_signature_value,
                'signature_algorithm': order.fiskaly_signature_algorithm,
                'signature_public_key': order.fiskaly_signature_public_key,
                'client_serial_number': order.fiskaly_client_serial_number
            }
            json['tss_info'] = tss_info
        return json
