from odoo import fields, Command
from odoo.tests import tagged

from odoo.addons.account_reports.tests.common import TestAccountReportsCommon


@tagged("post_install", "post_install_l10n", "-at_install")
class TestPeSales(TestAccountReportsCommon):
    @classmethod
    def setUpClass(cls, chart_template_ref="pe"):
        super().setUpClass(chart_template_ref=chart_template_ref)

        # To avoid breaking the constraint _check_l10n_latam_documents because we don't have document number on the moves
        # we set the field l10n_latam_use_document to false
        journals_to_update = cls.env['account.journal'].search([('l10n_latam_use_documents', '=', True)])
        journals_to_update.write({'l10n_latam_use_documents': False})

        move_types = ["out_invoice", "out_refund", "in_invoice", "in_refund"]
        date_invoice = "2022-07-01"
        moves_vals = [
            {
                "move_type": "entry",
                "date": date_invoice,
                "invoice_date_due": date_invoice,
                "l10n_pe_sunat_transaction_type": "opening",
                "line_ids": [
                    Command.create(
                        {'debit': 500.0, 'credit': 0.0, 'account_id': cls.company_data['default_account_expense'].id}),
                    Command.create(
                        {'debit': 0.0, 'credit': 500.0, 'account_id': cls.company_data['default_account_revenue'].id}),
                ]
            }
        ]
        moves_vals += [
            {
                "move_type": "entry",
                "date": date_invoice,
                "invoice_date_due": date_invoice,
                "l10n_pe_sunat_transaction_type": "closing",
                "line_ids": [
                    Command.create(
                        {'debit': 500.0, 'credit': 0.0, 'account_id': cls.company_data['default_account_expense'].id}),
                    Command.create(
                        {'debit': 0.0, 'credit': 500.0, 'account_id': cls.company_data['default_account_revenue'].id}),
                ]
            }
        ]
        for move_type in move_types:
            for partner in (cls.partner_a, cls.partner_b):
                moves_vals += [
                    {
                        "move_type": move_type,
                        "partner_id": partner.id,
                        "invoice_date": date_invoice,
                        "invoice_date_due": date_invoice,
                        "date": date_invoice,
                        "invoice_payment_term_id": False,
                        "invoice_line_ids": [
                            (0, 0, {
                                "name": f"test {move_type}",
                                "quantity": 1,
                                "price_unit": 10,
                                "tax_ids": False,
                            })
                        ],
                    },
                ]

        moves = cls.env["account.move"].create(moves_vals)
        moves.action_post()

        # Move in draft must be ignored
        moves[0].copy({"date": moves[0].date})

    def test_51_report(self):
        report = self.env.ref("account_reports.general_ledger_report")
        options = self._generate_options(
            report, fields.Date.from_string("2022-01-01"), fields.Date.from_string("2022-12-31")
        )

        self.maxDiff = None
        self.assertEqual(
            "\n".join(
                [
                    "|".join(line.split("|")[2:-3])
                    for line in self.env[report.custom_handler_model_name]
                    .l10n_pe_export_ple_51_to_txt(options)["file_content"]
                    .decode()
                    .split("\n")
                ]
            ),
            """
A1|6011000|||PEN|||00|MISC202207|0001|01/07/2022|01/07/2022|01/07/2022|MISC2022070001||500.00|0.00
A2|7011100|||PEN|||00|MISC202207|0001|01/07/2022|01/07/2022|01/07/2022|MISC2022070001||0.00|500.00
C1|6011000|||PEN|||00|MISC202207|0002|01/07/2022|01/07/2022|01/07/2022|MISC2022070002||500.00|0.00
C2|7011100|||PEN|||00|MISC202207|0002|01/07/2022|01/07/2022|01/07/2022|MISC2022070002||0.00|500.00
M1|7012100|||PEN|0|||INV2022|00001|01/07/2022|01/07/2022|01/07/2022|INV202200001||0.00|10.00
M2|1213000|||PEN|0|||INV2022|00001|01/07/2022|01/07/2022|01/07/2022|INV202200001||10.00|0.00
M1|7012100|||PEN|0|||INV2022|00002|01/07/2022|01/07/2022|01/07/2022|INV202200002||0.00|10.00
M2|1213010|||PEN|0|||INV2022|00002|01/07/2022|01/07/2022|01/07/2022|INV202200002||10.00|0.00
M1|7012100|||PEN|0|||RINV2022|00001|01/07/2022|01/07/2022|01/07/2022|RINV202200001||10.00|0.00
M2|1213000|||PEN|0|||RINV2022|00001|01/07/2022|01/07/2022|01/07/2022|RINV202200001||0.00|10.00
M1|7012100|||PEN|0|||RINV2022|00002|01/07/2022|01/07/2022|01/07/2022|RINV202200002||10.00|0.00
M2|1213010|||PEN|0|||RINV2022|00002|01/07/2022|01/07/2022|01/07/2022|RINV202200002||0.00|10.00
M1|6329000|||PEN|0||00|BILL202207|0001|01/07/2022|01/07/2022|01/07/2022|BILL2022070001||10.00|0.00
M2|4111000|||PEN|0||00|BILL202207|0001|01/07/2022|01/07/2022|01/07/2022|BILL2022070001||0.00|10.00
M1|6329000|||PEN|0||00|BILL202207|0002|01/07/2022|01/07/2022|01/07/2022|BILL2022070002||10.00|0.00
M2|4111010|||PEN|0||00|BILL202207|0002|01/07/2022|01/07/2022|01/07/2022|BILL2022070002||0.00|10.00
M1|6329000|||PEN|0||00|RBILL202207|0001|01/07/2022|01/07/2022|01/07/2022|RBILL2022070001||0.00|10.00
M2|4111000|||PEN|0||00|RBILL202207|0001|01/07/2022|01/07/2022|01/07/2022|RBILL2022070001||10.00|0.00
M1|6329000|||PEN|0||00|RBILL202207|0002|01/07/2022|01/07/2022|01/07/2022|RBILL2022070002||0.00|10.00
M2|4111010|||PEN|0||00|RBILL202207|0002|01/07/2022|01/07/2022|01/07/2022|RBILL2022070002||10.00|0.00
"""[1:],
        )

    def test_53_report(self):
        report = self.env.ref("account_reports.general_ledger_report")
        options = self._generate_options(
            report, fields.Date.from_string("2022-01-01"), fields.Date.from_string("2022-12-31")
        )

        self.assertEqual(
            self.env[report.custom_handler_model_name].l10n_pe_export_ple_53_to_txt(options)["file_content"]
            .decode().split("\n")[0],
            """20220101|0111000|Goods and securities delivered|00||||1|""",
        )
