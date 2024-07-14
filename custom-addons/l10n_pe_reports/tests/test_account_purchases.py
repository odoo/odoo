from datetime import timedelta

from odoo import fields
from odoo.tests import tagged

from odoo.addons.account_reports.tests.common import TestAccountReportsCommon


@tagged("post_install", "post_install_l10n", "-at_install")
class TestPePurchase(TestAccountReportsCommon):
    @classmethod
    def setUpClass(cls, chart_template_ref="pe"):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.purchase_taxes = cls._get_purchase_taxes()
        cls.company_data['default_journal_purchase'].l10n_latam_use_documents = True

    @classmethod
    def _get_purchase_taxes(cls):
        taxes = cls.env["account.tax"]
        for tax in ["igv_18", "igv_18_included", "exo", "ina", "gra"]:
            taxes += cls.env.ref(f"account.{cls.env.company.id}_purchase_tax_{tax}")

        return taxes

    def _prepare_purchase_moves(self, invoice_type=False, refund_type=False):
        date_invoice = "2022-07-01"
        moves_vals = []
        for i, tax in enumerate(self.purchase_taxes):
            moves_vals += [
                {
                    "move_type": "in_invoice",
                    "l10n_latam_document_number": "INV/2022/07/%s" % (i + 1),
                    "partner_id": self.partner_a.id,
                    "invoice_date": date_invoice,
                    "invoice_date_due": date_invoice,
                    "date": date_invoice,
                    "invoice_payment_term_id": False,
                    "l10n_latam_document_type_id": (invoice_type or self.env.ref("l10n_pe.document_type01")).id,
                    "l10n_pe_usage_type_id": self.env.ref("l10n_pe_reports.ple_usage_type_00").id,
                    "invoice_line_ids": [
                        (0, 0, {
                            "name": f"test {tax.amount}",
                            "quantity": 1,
                            "price_unit": 10 + 1 * i,
                            "tax_ids": [(6, 0, tax.ids)],
                        })
                    ],
                },
            ]

        moves = self.env["account.move"].create(moves_vals)
        moves.action_post()
        number = 1
        for move in moves:
            move_reversal = (
                self.env["account.move.reversal"]
                .with_context(active_ids=move.ids, active_model="account.move")
                .create(
                    {
                        "reason": "Testing",
                        "date": move.invoice_date + timedelta(days=1),
                        "journal_id": move.journal_id.id,
                    }
                )
            )
            refund = self.env["account.move"].browse(move_reversal.reverse_moves()["res_id"])
            refund.l10n_latam_document_type_id = refund_type or self.env.ref("l10n_pe.document_type07")
            refund.l10n_latam_document_number = "FFF %s" % str(number).zfill(4)
            refund.l10n_pe_usage_type_id = self.env.ref("l10n_pe_reports.ple_usage_type_00")
            refund.action_post()
            number += 1
        return moves

    def test_purchase_report_8_1(self):
        (self.partner_a | self.partner_b).write({"country_id": self.env.ref("base.pe").id})
        moves = self._prepare_purchase_moves()
        # Moves with document type in ("91", "97", "98") must be ignored. Created to ensure that are not considered
        # in the 8.1 report
        self._prepare_purchase_moves(
            self.env.ref("l10n_pe.document_type91"), self.env.ref("l10n_pe.document_type97")
        )
        # Moves for not Peruvian partner must be ignored
        partner_c = self.partner_a.copy({"country_id": self.env.ref("base.mx").id})
        moves[0].copy({"partner_id": partner_c.id})
        report = self.env.ref("l10n_pe_reports.tax_report_ple_purchase_8_1")

        options = self._generate_options(
            report, fields.Date.from_string("2022-01-01"), fields.Date.from_string("2022-12-31")
        )
        options.update({"journal_type": "purchase"})
        self.maxDiff = None
        self.assertEqual(
            "\n".join(
                [
                    "|".join(line.split("|")[3:])
                    for line in self.env[report.custom_handler_model_name]
                    .export_to_txt(options)["file_content"]
                    .decode()
                    .split("\r\n")
                ]
            ),
            """
|01/07/2022|01/07/2022|01|INV/2022/07/||1||0||partner_a|10.0|1.8|0.00|0.00|0.00|0.00|0.00|0.00|0.00|0.00|11.8|PEN||||||||||||||
|01/07/2022|01/07/2022|01|INV/2022/07/||2||0||partner_a|9.32|1.68|0.00|0.00|0.00|0.00|0.00|0.00|0.00|0.00|11.0|PEN||||||||||||||
|01/07/2022|01/07/2022|01|INV/2022/07/||3||0||partner_a|0.0|0.00|0.00|0.00|0.00|0.00|12.0|0.00|0.00|0.00|12.0|PEN||||||||||||||
|01/07/2022|01/07/2022|01|INV/2022/07/||4||0||partner_a|0.0|0.00|0.00|0.00|0.00|0.00|13.0|0.00|0.00|0.00|13.0|PEN||||||||||||||
|01/07/2022|01/07/2022|01|INV/2022/07/||5||0||partner_a|0.0|0.00|0.00|0.00|0.00|0.00|14.0|0.00|0.00|0.00|14.0|PEN||||||||||||||
|02/07/2022|02/07/2022|07|FFF||1||0||partner_a|-10.0|-1.8|0.00|0.00|0.00|0.00|0.00|0.00|0.00|0.00|-11.8|PEN||01/07/2022|01|INV/2022/07/||1||||||||
|02/07/2022|02/07/2022|07|FFF||2||0||partner_a|-9.32|-1.68|0.00|0.00|0.00|0.00|0.00|0.00|0.00|0.00|-11.0|PEN||01/07/2022|01|INV/2022/07/||2||||||||
|02/07/2022|02/07/2022|07|FFF||3||0||partner_a|0.0|0.00|0.00|0.00|0.00|0.00|-12.0|0.00|0.00|0.00|-12.0|PEN||01/07/2022|01|INV/2022/07/||3||||||||
|02/07/2022|02/07/2022|07|FFF||4||0||partner_a|0.0|0.00|0.00|0.00|0.00|0.00|-13.0|0.00|0.00|0.00|-13.0|PEN||01/07/2022|01|INV/2022/07/||4||||||||
|02/07/2022|02/07/2022|07|FFF||5||0||partner_a|0.0|0.00|0.00|0.00|0.00|0.00|-14.0|0.00|0.00|0.00|-14.0|PEN||01/07/2022|01|INV/2022/07/||5||||||||
"""[
                1:
            ],
        )

    def test_purchase_report_8_2(self):
        self.partner_a.write({"country_id": self.env.ref("base.mx").id})
        self._prepare_purchase_moves(
            self.env.ref("l10n_pe.document_type91"), self.env.ref("l10n_pe.document_type97")
        )
        # Moves with document type not in ("91", "97", "98") must be ignored
        self._prepare_purchase_moves()
        report = self.env.ref("l10n_pe_reports.tax_report_ple_purchase_8_2")

        options = self._generate_options(
            report, fields.Date.from_string("2022-01-01"), fields.Date.from_string("2022-12-31")
        )
        options.update({"journal_type": "purchase"})

        self.maxDiff = None
        self.assertEqual(
            "\n".join(
                [
                    "|".join(line.split("|")[2:])
                    for line in self.env[report.custom_handler_model_name]
                    .export_to_txt(options)["file_content"]
                    .decode()
                    .split("\r\n")
                ]
            ),
            """
01/07/2022|91|INV/2022/07/|1|10.0||11.8|||||1.8|PEN||9493|partner_a|||||||0.00|0.00|0.00|0.00|0.00|05||00||||
01/07/2022|91|INV/2022/07/|2|9.32||11.0|||||1.68|PEN||9493|partner_a|||||||0.00|0.00|0.00|0.00|0.00|05||00||||
01/07/2022|91|INV/2022/07/|3|0.0||12.0||||||PEN||9493|partner_a|||||||0.00|0.00|0.00|0.00|0.00|05|12.0|00||||
01/07/2022|91|INV/2022/07/|4|0.0||13.0||||||PEN||9493|partner_a|||||||0.00|0.00|0.00|0.00|0.00|05||00||||
01/07/2022|91|INV/2022/07/|5|0.0||14.0||||||PEN||9493|partner_a|||||||0.00|0.00|0.00|0.00|0.00|05||00||||
02/07/2022|97|FFF|1|-10.0||-11.8|||||-1.8|PEN||9493|partner_a|||||||0.00|0.00|0.00|0.00|0.00|05||00||||
02/07/2022|97|FFF|2|-9.32||-11.0|||||-1.68|PEN||9493|partner_a|||||||0.00|0.00|0.00|0.00|0.00|05||00||||
02/07/2022|97|FFF|3|0.0||-12.0||||||PEN||9493|partner_a|||||||0.00|0.00|0.00|0.00|0.00|05|-12.0|00||||
02/07/2022|97|FFF|4|0.0||-13.0||||||PEN||9493|partner_a|||||||0.00|0.00|0.00|0.00|0.00|05||00||||
02/07/2022|97|FFF|5|0.0||-14.0||||||PEN||9493|partner_a|||||||0.00|0.00|0.00|0.00|0.00|05||00||||
"""[
                1:
            ],
        )
