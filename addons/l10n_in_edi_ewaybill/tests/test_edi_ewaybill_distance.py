from contextlib import contextmanager
from unittest.mock import patch

from odoo.addons.l10n_in_edi.tests.test_edi_json import TestEdiJson
from odoo.addons.l10n_in_edi_ewaybill.models.account_edi_format import AccountEdiFormat
from odoo.tests import tagged


@tagged("post_install_l10n", "post_install", "-at_install")
class TestEdiEwaybillJson(TestEdiJson):

    @contextmanager
    def mockEwaybillGateway(self):

        def _l10n_in_edi_ewaybill_generate(self, company, json_payload={}):
            return {
                "status_cd": "1",
                "status_desc": "EWAYBILL request succeeds",
                "data": {
                    "ewayBillNo": 123456789012,
                    "ewayBillDate": "11/06/2024 06:37:15 AM",
                    "validUpto": "12/06/2024 06:37:15 AM",
                    "alert": ", Distance between these two pincodes is 118, ",
                }
            }

        with patch.object(AccountEdiFormat, "_l10n_in_edi_ewaybill_generate", side_effect=_l10n_in_edi_ewaybill_generate):
            yield

    def test_edi_distance(self):
        self.invoice.write(
            {
                "l10n_in_type_id": self.env.ref(
                    "l10n_in_edi_ewaybill.type_tax_invoice_sub_type_supply"
                ),
                "l10n_in_distance": 0,
                "l10n_in_mode": "1",
                "l10n_in_vehicle_no": "GJ11AA1234",
                "l10n_in_vehicle_type": "R",
            }
        )
        with self.mockEwaybillGateway():
            self.invoice.l10n_in_edi_ewaybill_send()
            self.invoice.action_process_edi_web_services(with_commit=False)
        expected_distance = 118
        self.assertEqual(self.invoice.l10n_in_distance, expected_distance)
