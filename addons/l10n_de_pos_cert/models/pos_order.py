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
    fiskaly_client_serial = fields.Char(string="Client serial", readonly=True, copy=False)

    @api.model
    def _order_fields(self, ui_order):
        fields = super(PosOrder, self)._order_fields(ui_order)
        fields['fiskaly_transaction_uuid'] = ui_order['fiskaly_uuid']
        fields['fiskaly_transaction_number'] = ui_order['tss_info']['number']
        fields['fiskaly_time_start'] = ui_order['tss_info']['timeStart']
        fields['fiskaly_time_end'] = ui_order['tss_info']['timeEnd']
        fields['fiskaly_certificate_serial'] = ui_order['tss_info']['certificateSerial']
        fields['fiskaly_timestamp_format'] = ui_order['tss_info']['timestampFormat']
        fields['fiskaly_signature_value'] = ui_order['tss_info']['signatureValue']
        fields['fiskaly_signature_algorithm'] = ui_order['tss_info']['signatureAlgorithm']
        fields['fiskaly_signature_public_key'] = ui_order['tss_info']['signaturePublicKey']
        fields['fiskaly_client_serial'] = ui_order['tss_info']['clientSerialnumber']

        return fields
