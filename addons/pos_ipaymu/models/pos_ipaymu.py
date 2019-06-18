# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import requests
# from requests import Request
import werkzeug
from odoo import models, fields, api, _
from odoo.tools.float_utils import float_compare

_logger = logging.getLogger(__name__)


class BarcodeRule(models.Model):
    _inherit = 'barcode.rule'

    type = fields.Selection(selection_add=[
        ('credit', 'Credit Card')
    ])


class PosIPaymuConfiguration(models.Model):
    _name = 'pos_ipaymu.configuration'
    _description = "IPaymu Payment Method configuration"

    name = fields.Char(required=True, help='Name of this IPaymu configuration')
    merchant_api_key = fields.Char(string='Merchant API Key', required=True, help='ID of the merchant to authenticate him on the payment provider server')

    @api.model
    def get_qr_code(self, data):
        """
        if valid request returns:
            Status          Status message
            TrxId
            QrCode
        else returns:
            Status          Error message

        :param data:
        :type data: dict(str, any)
        :return: request response or error code
        :rtype: dict(str, any)
        """
        api_key = self.browse(data['ipaymu_config_id']).merchant_api_key
        url = 'https://my.ipaymu.com/api/tagqr'
        data = {'key': api_key, 'request': 'generate', 'price': data['amount'], 'uniqid': data['uniqid'], 'notify_url': False}
        r = requests.post(url, data = data)
        r.raise_for_status()
        response = r.json()
        if 'QrCode' in response:
            return {
                    'Status': 'OK',
                    'TrxId': response['TrxId'],
                    'QrCode': response['QrCode'],
                    }
        else:
            return {'Status': 'AuthorisationError'}
        return response

    @api.model
    def get_status_payment(self, data):
        """
        if valid returns:
            Status          Status code
                -1              Transaction is being processed
                0               Pending
                1               Successful
                2               Cancel
                3               Refund
                6               Waiting for Settlement
            Keterangan      Status message
                -1 => Sedang diproses
                0 => Pending
                1 => Berhasil
                2 => Batal
                3 => Refund
                6 => Menunggu Settlement
            Pengirim        Senders Username
            Penerima        Receivers Username
            Nominal         Transactiebedrag
            Waktu           Transactie datum + tijd
            Tipe            Transactietype (TAG QR)
        else returns:
            Status          Error code
                -1001
            Keterangan      Error message
                Transaksi tidak ditemukan => Transaction not found

        :param data:
        :type data: dict(str, any)
        :return: payment status
        :rtype: dict(str, str)
        """
        api_key = self.browse(data['ipaymu_config_id']).merchant_api_key
        url = 'https://my.ipaymu.com/api/transaksi'
        headers = {
                'accept': 'application/json',
                }
        request_data = {
                'key': api_key,
                'id': data['trx_id'],
                'format': 'json',
                }
        r = requests.post(url, data = request_data, headers = headers)
        r.raise_for_status()
        response = r.json()
        if 'Status' in response and response['Status'] >= -1:
            status = response['Status']
            if status == 0:
                status = 'waitingScan'
            elif status == 1:
                status = 'done'
            elif status == 2:
                status = 'retry'
            elif status == -1:
                status = 'processing'

            print(response)
            return {
                    'trx_id': data['trx_id'],
                    'Status': status,
                    'Nominal': float(response['Nominal'])
                    }
        return response


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    pos_ipaymu_config_id = fields.Many2one('pos_ipaymu.configuration', string='IPaymu Credentials', help='The configuration of IPaymu used for this journal')


