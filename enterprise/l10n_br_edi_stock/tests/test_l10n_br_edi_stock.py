# Part of Odoo. See LICENSE file for full copyright and licensing details.
import json

from odoo import Command
from odoo.addons.l10n_br_edi.tests.test_l10n_br_edi import TestL10nBREDICommon
from odoo.tests import tagged


@tagged("post_install_l10n", "-at_install", "post_install")
class TestL10nBrEDIStock(TestL10nBREDICommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.product_screens.barcode = "12345678"
        cls.product_screens.is_storable = True
        cls.product_screens.product_variant_id.weight = 7
        cls.package_type = cls.env["stock.package.type"].create(
            {"name": "Box", "l10n_br_brand": "BR brand", "base_weight": 3}
        )
        cls.sale_order = cls.env["sale.order"].create(
            {
                "partner_id": cls.partner_customer.id,
                "order_line": [
                    Command.create(
                        {
                            "product_id": cls.product_screens.product_variant_id.id,
                            "tax_id": False,
                            "product_uom_qty": 12,
                        }
                    ),
                ],
                "l10n_br_edi_freight_model": "CIF",
            }
        )

    def test_01_nfe_with_transport_info(self):
        self.sale_order.action_confirm()
        picking = self.sale_order.order_line.move_ids.picking_id[0]
        picking.move_ids[0].quantity = picking.move_ids[0].product_uom_qty
        picking.action_put_in_pack()
        picking.move_line_ids.result_package_id.package_type_id = self.package_type
        picking.button_validate()

        invoice = self.sale_order._create_invoices()
        invoice.fiscal_position_id = self.avatax_fp  # only set it on the invoice to avoid patching out calls on sale order
        invoice.l10n_br_package_ids = invoice.l10n_br_related_package_ids  # select all related packages

        self.partner_customer.property_account_position_id = self.avatax_fp
        with self.with_patched_account_move("_l10n_br_iap_request"), self.with_patched_account_move("_l10n_br_call_avatax_taxes"):
            invoice.action_post()
        invoice.l10n_br_edi_avatax_data = json.dumps({"header": {}})  # normally set by account.external.tax.mixin
        invoice.l10n_br_plate_number = "12345678"

        wizard = self.env["account.move.send.wizard"].create({"move_id": invoice.id})

        with self.with_patched_account_move("_l10n_br_iap_request") as patched_submit:
            wizard.action_send_and_print(allow_fallback_pdf=True)  # allow_fallback_pdf to avoid raising on errors

        sent_request = patched_submit.call_args.args[2]

        self.assertIn("volumes", sent_request["header"]["goods"]["transport"], "Transport data wasn't sent in request.")
        self.assertEqual(len(sent_request["header"]["goods"]["transport"]["volumes"]), 1, "Exactly one volume should be sent.")
        self.assertDictEqual(
            sent_request["header"]["goods"]["transport"]["vehicle"], {"automobile": {"licensePlate": "12345678"}}
        )
        self.assertDictEqual(
            sent_request["header"]["goods"]["transport"]["volumes"][0],
            {
                "qVol": 1,
                "volumeNumeration": "1 of 1",
                "netWeight": 7.0 * 12,
                "grossWeight": 7.0 * 12 + 3,
                "brand": "BR brand",
                "specie": "Box",
            },
        )
