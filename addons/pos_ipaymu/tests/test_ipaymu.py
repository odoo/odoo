# -*- coding: utf-8 -*-

from unittest.mock import patch

from odoo.tests import tagged
from odoo.addons.pos_ipaymu.tests.common import MockResponse, TestPosIPaymuCommon, mocked_ipaymu_requests_post


@tagged('post_install', '-at_install')
class TestPointOfSaleFlow(TestPosIPaymuCommon):

    @patch('requests.post', side_effect=mocked_ipaymu_requests_post)
    def test_get_qr_code(self, mock_post):
        self.assertEqual(self.ipaymu_config.get_qr_code(
            {
                'ipaymu_config_id': self.ipaymu_config.id,
                'amount': 50,
                'uniqid': 'dcadas'
            }), {
                'Status': "OK",
                'TrxId': 3900008,
                'QrCode': 'VBORw0KGgoAAAANSUhEUgAAAV4AAAFeCAIAAABCSeBNAAAACXBIWXMAAA7EAAAOxAGVKw4bAAAFlklEQVR4nO3dwW4TMRhGUVrx/o9csauCdDc2ePgdztkXTTzRVTYf/vj6+voB8LvPf/0AwETSAARpAII0AEEagCANQJAGIEgDEKQBCNIABGkAgjQAQRqAIA1AkAYgSAMQfm78zeenoGy68T/OWXrd5z6gb922vZfiuIEgDUCQBiBIAxCkAQjSAARpAII0AEEagCANQJAGIEgDEKQBCNIAhJ1R9pIbZ8hLhoyFz02nb3yDNz7zkge+dSO+1sA00gAEaQCCNABBGoAgDUCQBiBIAxCkAQjSAARpAII0AEEagCANQDg+yl4yZOA8ZNJ7bmftnF85jTTiUIBppAEI0gAEaQCCNABBGoAgDUCQBiBIAxCkAQjSAARpAII0AEEagDBrlM2rczvrc/vfIQNn/pwXCQRpAII0AEEagCANQJAGIEgDEKQBCNIABGkAgjQAQRqAIA1AkAYgSAMQpAEI0gAEaQCCNABBGoAgDUCQBiBIAxCkAQjSAARpAII0AEEagCANQJh1U/a5G5x5de5a7Rvf4I3P/AC/GoAgDUCQBiBIAxCkAQjSAARpAII0AEEagCANQJAGIEgDEKQBCNIAhOOj7KX9L6/OTafPvZRzz3zuMUhOEAjSAARpAII0AEEagCANQJAGIEgDEKQBCNIABGkAgjQAQRqAIA1A2Bllu1n4vzJkZ+1b9zC/GoAgDUCQBiBIAxCkAQjSAARpAII0AEEagCANQJAGIEgDEKQBCNIAhJ1R9pBriIfcDc2rIec8ZME9ZM++Z8SLBKaRBiBIAxCkAQjSAARpAII0AEEagCANQJAGIEgDEKQBCNIABGkAws4oe8m5qem5/e+QeeyQgfOSIUe35Nx0+sbT+Hbflw94gDQAQRqAIA1AkAYgSAMQpAEI0gAEaQCCNABBGoAgDUCQBiBIAxB2Rtk3Tk2HXKs95OjOncaQIfmQc776NEY8OjCNNABBGoAgDUCQBiBIAxCkAQjSAARpAII0AEEagCANQJAGIEgDEI7flL3k3J3Fb7+zPscHHPgvPzD39qsBCNIABGkAgjQAQRqAIA1AkAYgSAMQpAEI0gAEaQCCNABBGoAgDUCYNcpeMmRnfW5IPsSQD3jjYP+cB75I9x0K8ABpAII0AEEagCANQJAGIEgDEKQBCNIABGkAgjQAQRqAIA1AkAYgzBpl37hZvvGZb5whLxmy4L56Gz7raYAhpAEI0gAEaQCCNABBGoAgDUCQBiBIAxCkAQjSAARpAII0AEEagPCxsSmeth69yJD97xKv+3Z73w1vHQjSAARpAII0AEEagCANQJAGIEgDEKQBCNIABGkAgjQAQRqAIA1AOH5T9o0XSS+5cbM85LrnIUPyIR9wyNF9u+9rDTxAGoAgDUCQBiBIAxCkAQjSAARpAII0AEEagCANQJAGIEgDEKQBCMdH2UuGDJxvHJIPGQufc+4xhnzAaQvuEYcCTCMNQJAGIEgDEKQBCNIABGkAgjQAQRqAIA1AkAYgSAMQpAEI0gCEWaNsXr39RdJLhizlb1xw7xnxOYFppAEI0gAEaQCCNABBGoAgDUCQBiBIAxCkAQjSAARpAII0AEEagGCUPdcDtyH/9cc4Z8hjDLnP2k3ZwL8hDUCQBiBIAxCkAQjSAARpAII0AEEagCANQJAGIEgDEKQBCNIAhFmj7CG3Ib+9Gxfcb//MQzb43/xqAII0AEEagCANQJAGIEgDEKQBCNIABGkAgjQAQRqAIA1AkAYgSAMQPjbWnUPuLL7RuZXuOTcu5YcMnK9+gyMeHZhGGoAgDUCQBiBIAxCkAQjSAARpAII0AEEagCANQJAGIEgDEKQBCDujbODt+dUABGkAgjQAQRqAIA1AkAYgSAMQpAEI0gAEaQCCNABBGoAgDUC',
                }, "no qr code generated")

    @patch('requests.post', side_effect=mocked_ipaymu_requests_post)
    def test_get_payment_status(self, mock_post):
        nominal = 100
        id = 3900008

        MockResponse.reset()
        self.assertEqual(self.ipaymu_config.get_status_payment(
            {
                'ipaymu_config_id': self.ipaymu_config.id,
                'trx_id': id,
            }),{
                        "Status": -1001,
                        "Keterangan": "Transaksi tidak ditemukan",
                        })
            
        self.ipaymu_config.get_qr_code(
            {
                'ipaymu_config_id': self.ipaymu_config.id,
                'amount': nominal,
                'uniqid': 'dcadas'
            })

        self.assertEqual(self.ipaymu_config.get_status_payment(
            {
                'ipaymu_config_id': self.ipaymu_config.id,
                'trx_id': id,
            }),{
                        "trx_id": id,
                        "Status": 'waitingScan',
                        "Nominal": nominal,
                        #"Biaya": "500",
                        #"Terbayar": nominal,
                        })
