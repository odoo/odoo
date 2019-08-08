# -*- coding: utf-8 -*-
from odoo.addons.point_of_sale.tests.common import TestPointOfSaleCommon

from re import compile as re_compile

class MockResponse:

    api_key = '0oLuh.EV6dF3FZRqn5t8aFDZ2sFoH1'
    trx_id = 3900008
    nominal = 0
    iteration = 0
    iteration_done = 5

    @classmethod
    def reset(cls):
        cls.nominal = 0
        cls.iteration = 0

    @classmethod
    def _add_iteration(cls):
        cls.iteration += 1

    @classmethod
    def _set_nominal(cls, nominal):
        cls.nominal = nominal

    def __init__(self, msg_type, data):
        if msg_type == 'qr':
            self._set_nominal(data['price'])
            self.json_data = {
                    'Status': 200,
                    'Keterangan': "OK",
                    'TrxId': self.trx_id,
                    'QrCode': 'VBORw0KGgoAAAANSUhEUgAAAV4AAAFeCAIAAABCSeBNAAAACXBIWXMAAA7EAAAOxAGVKw4bAAAFlklEQVR4nO3dwW4TMRhGUVrx/o9csauCdDc2ePgdztkXTTzRVTYf/vj6+voB8LvPf/0AwETSAARpAII0AEEagCANQJAGIEgDEKQBCNIABGkAgjQAQRqAIA1AkAYgSAMQfm78zeenoGy68T/OWXrd5z6gb922vZfiuIEgDUCQBiBIAxCkAQjSAARpAII0AEEagCANQJAGIEgDEKQBCNIAhJ1R9pIbZ8hLhoyFz02nb3yDNz7zkge+dSO+1sA00gAEaQCCNABBGoAgDUCQBiBIAxCkAQjSAARpAII0AEEagCANQDg+yl4yZOA8ZNJ7bmftnF85jTTiUIBppAEI0gAEaQCCNABBGoAgDUCQBiBIAxCkAQjSAARpAII0AEEagDBrlM2rczvrc/vfIQNn/pwXCQRpAII0AEEagCANQJAGIEgDEKQBCNIABGkAgjQAQRqAIA1AkAYgSAMQpAEI0gAEaQCCNABBGoAgDUCQBiBIAxCkAQjSAARpAII0AEEagCANQJh1U/a5G5x5de5a7Rvf4I3P/AC/GoAgDUCQBiBIAxCkAQjSAARpAII0AEEagCANQJAGIEgDEKQBCNIAhOOj7KX9L6/OTafPvZRzz3zuMUhOEAjSAARpAII0AEEagCANQJAGIEgDEKQBCNIABGkAgjQAQRqAIA1A2Bllu1n4vzJkZ+1b9zC/GoAgDUCQBiBIAxCkAQjSAARpAII0AEEagCANQJAGIEgDEKQBCNIAhJ1R9pBriIfcDc2rIec8ZME9ZM++Z8SLBKaRBiBIAxCkAQjSAARpAII0AEEagCANQJAGIEgDEKQBCNIABGkAws4oe8m5qem5/e+QeeyQgfOSIUe35Nx0+sbT+Hbflw94gDQAQRqAIA1AkAYgSAMQpAEI0gAEaQCCNABBGoAgDUCQBiBIAxB2Rtk3Tk2HXKs95OjOncaQIfmQc776NEY8OjCNNABBGoAgDUCQBiBIAxCkAQjSAARpAII0AEEagCANQJAGIEgDEI7flL3k3J3Fb7+zPscHHPgvPzD39qsBCNIABGkAgjQAQRqAIA1AkAYgSAMQpAEI0gAEaQCCNABBGoAgDUCYNcpeMmRnfW5IPsSQD3jjYP+cB75I9x0K8ABpAII0AEEagCANQJAGIEgDEKQBCNIABGkAgjQAQRqAIA1AkAYgzBpl37hZvvGZb5whLxmy4L56Gz7raYAhpAEI0gAEaQCCNABBGoAgDUCQBiBIAxCkAQjSAARpAII0AEEagPCxsSmeth69yJD97xKv+3Z73w1vHQjSAARpAII0AEEagCANQJAGIEgDEKQBCNIABGkAgjQAQRqAIA1AOH5T9o0XSS+5cbM85LrnIUPyIR9wyNF9u+9rDTxAGoAgDUCQBiBIAxCkAQjSAARpAII0AEEagCANQJAGIEgDEKQBCMdH2UuGDJxvHJIPGQufc+4xhnzAaQvuEYcCTCMNQJAGIEgDEKQBCNIABGkAgjQAQRqAIA1AkAYgSAMQpAEI0gCEWaNsXr39RdJLhizlb1xw7xnxOYFppAEI0gAEaQCCNABBGoAgDUCQBiBIAxCkAQjSAARpAII0AEEagGCUPdcDtyH/9cc4Z8hjDLnP2k3ZwL8hDUCQBiBIAxCkAQjSAARpAII0AEEagCANQJAGIEgDEKQBCNIAhFmj7CG3Ib+9Gxfcb//MQzb43/xqAII0AEEagCANQJAGIEgDEKQBCNIABGkAgjQAQRqAIA1AkAYgSAMQPjbWnUPuLL7RuZXuOTcu5YcMnK9+gyMeHZhGGoAgDUCQBiBIAxCkAQjSAARpAII0AEEagCANQJAGIEgDEKQBCDujbODt+dUABGkAgjQAQRqAIA1AkAYgSAMQpAEI0gAEaQCCNABBGoAgDUC',
                    'QrData': 'OTQ0OTA5MDkwMDMx'
                    }
            self.status_code = 200
        elif msg_type == 'status':
            self.status_code = 200
            if self.nominal == 0 or data['id'] != self.trx_id:
                self.json_data = {
                        "Status": -1001,
                        "Keterangan": "Transaksi tidak ditemukan",
                        }
            elif self.iteration == self.iteration_done:
                self.json_data = {
                        "Status": 1,
                        "Keterangan": "Berhasil",
                        "Pengirim": "pengirim@gmail.com",
                        "Penerima": "penerima@gmail.com",
                        "Nominal": str(self.nominal),
                        "Biaya": "500",
                        "Terbayar": self.nominal,
                        "Waktu": "2019-05-31 15:56:50",
                        "Tipe": "TAG QR"
                        }
            else:
                self._add_iteration()
                self.json_data = {
                        "Status": 0,
                        "Keterangan": "Pending",
                        "Pengirim": "pengirim@gmail.com",
                        "Penerima": "penerima@gmail.com",
                        "Nominal": str(self.nominal),
                        "Biaya": "500",
                        "Terbayar": self.nominal,
                        "Waktu": "2019-05-31 15:56:50",
                        "Tipe": "TAG QR"
                        }

        else:
            self.json_data = None
        self.status_code = 404

    def json(self):
        return self.json_data
    def raise_for_status(self):
        return True


def mocked_ipaymu_requests_post(*args, **kwargs):
    generate_url = 'https://my.ipaymu.com/api/tagqr'
    get_status_url = 'https://my.ipaymu.com/api/transaksi'


    if generate_url == args[0]:
        return MockResponse('qr', kwargs['data'])
    if get_status_url == args[0]:
        return MockResponse('status', kwargs['data'])

    return MockResponse(None)

class TestPosIPaymuCommon(TestPointOfSaleCommon):

    def setUp(self):
        super().setUp()

        # Create the payment methods
        self.ipaymu_config = self.env['pos_ipaymu.configuration'].create({
            'name': 'Ipaymu Test',
            'merchant_api_key': '0oLuh.EV6dF3FZRqn5t8aFDZ2sFoH1'
            })
        ipaymu_journal = self.env['account.journal'].create({
            'name': 'IPaymu',
            'type': 'bank',
            'code': 'IP',
            'journal_user': True,
            'pos_ipaymu_config_id': self.ipaymu_config.id,
            })
        self.pos_config.journal_ids |= ipaymu_journal
