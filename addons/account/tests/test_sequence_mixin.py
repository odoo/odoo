import json
from functools import reduce
from unittest.mock import Mock, patch

import psycopg
from dateutil.relativedelta import relativedelta
from freezegun import freeze_time

from odoo import SUPERUSER_ID, Command, api, fields
from odoo.exceptions import ValidationError
from odoo.tests import Form, TransactionCase, tagged
from odoo.tools import mute_logger

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


class TestSequenceMixinCommon(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_data["company"].account_config_id.write(
            {"fiscalyear_last_day": "31", "fiscalyear_last_month": "3"}
        )
        cls.test_move = cls.create_move()

    @classmethod
    def create_move(cls, date=None, journal=None, name=None, post=False):
        move = cls.env["account.move"].create(
            {
                "move_type": "entry",
                "date": date or "2016-01-01",
                "line_ids": [
                    (
                        0,
                        None,
                        {
                            "name": "line",
                            "account_id": cls.company_data[
                                "default_account_revenue"
                            ].id,
                        },
                    ),
                ],
            }
        )
        if journal:
            move.name = False
            move.journal_id = journal
        if name:
            move.name = name
        if post:
            move.action_post()
        return move

    def assertMoveName(self, move, expected_name):
        if move.name_placeholder:
            self.assertFalse(
                move.name,
                f"This move is potentially the first of the sequence, it shouldn't have a name while it is not posted. Got '{move.name}'.",
            )
            self.assertEqual(
                move.name_placeholder,
                expected_name,
                f"This move is potentially the first of the sequence, it doesn't have a name but a placeholder name which is currently '{move.name_placeholder}'. You expected '{expected_name}'.",
            )
        else:
            self.assertEqual(
                move.name,
                expected_name,
                f"Expected '{expected_name}' but got '{move.name}'.",
            )


@tagged("post_install", "-at_install")
class TestSequenceMixin(TestSequenceMixinCommon):
    def assertNameAtDate(self, date, name):
        test = self.create_move(date=date)
        test.action_post()
        self.assertEqual(test.name, name)
        return test

    def set_sequence(self, date, name):
        return self.create_move(date=date, name=name)._post(soft=False)

    def test_sequence_change_date(self):
        self.assertEqual(self.test_move.state, "draft")
        self.assertEqual(self.test_move.name_placeholder, "MISC/15-16/01/0001")
        self.assertEqual(fields.Date.to_string(self.test_move.date), "2016-01-01")

        self.test_move.date = "2020-02-02"
        self.assertMoveName(self.test_move, "MISC/19-20/02/0001")

        self.test_move.name = "MyMISC/2020/0000001"
        self.test_move.action_post()
        self.assertMoveName(self.test_move, "MyMISC/2020/0000001")

        self.test_move.action_draft()
        self.test_move.date = "2020-01-02"
        self.test_move.action_post()
        self.assertMoveName(self.test_move, "MyMISC/2020/0000001")

    def test_sequence_change_date_with_quick_edit_mode(self):
        self.env.company.account_config_id.quick_edit_mode = "out_and_in_invoices"
        self.env.company.account_config_id.fiscalyear_last_day = 30
        self.env.company.account_config_id.fiscalyear_last_month = "12"

        bill = self.env["account.move"].create(
            {
                "partner_id": 1,
                "move_type": "in_invoice",
                "date": "2016-01-01",
                "line_ids": [
                    Command.create(
                        {
                            "name": "line",
                            "account_id": self.company_data[
                                "default_account_revenue"
                            ].id,
                        }
                    ),
                ],
            }
        )
        self.assertMoveName(bill, "BILL/15-16/01/0001")
        bill = bill.copy({"date": "2016-02-01"})

        self.assertMoveName(bill, "BILL/15-16/02/0001")
        with Form(bill) as bill_form:
            bill_form.date = "2016-02-02"
            self.assertMoveName(bill_form, "BILL/15-16/02/0001")
            bill_form.date = "2016-03-01"
            self.assertMoveName(bill_form, "BILL/15-16/03/0001")
            bill_form.date = "2017-01-01"
            self.assertMoveName(bill_form, "BILL/16-17/01/0001")

        invoice = self.env["account.move"].create(
            {
                "partner_id": 1,
                "move_type": "out_invoice",
                "date": "2016-01-01",
                "line_ids": [
                    Command.create(
                        {
                            "name": "line",
                            "account_id": self.company_data[
                                "default_account_revenue"
                            ].id,
                        }
                    ),
                ],
            }
        )

        self.assertMoveName(invoice, "INV/15-16/0001")
        with Form(invoice) as invoice_form:
            invoice_form.date = "2016-01-02"
            self.assertMoveName(invoice_form, "INV/15-16/0001")
            invoice_form.date = "2016-02-02"
            self.assertMoveName(invoice_form, "INV/15-16/0001")
            invoice_form.date = "2017-01-01"
            self.assertMoveName(invoice_form, "INV/16-17/0001")

    def test_sequence_empty_editable_with_quick_edit_mode(self):
        self.env.company.account_config_id.quick_edit_mode = "in_invoices"

        bill_1 = self.env["account.move"].create(
            {
                "partner_id": 1,
                "move_type": "in_invoice",
                "date": "2016-01-01",
                "invoice_date": "2016-01-01",
                "line_ids": [
                    Command.create(
                        {
                            "name": "line",
                            "account_id": self.company_data[
                                "default_account_revenue"
                            ].id,
                        }
                    ),
                ],
            }
        )
        self.assertMoveName(bill_1, "BILL/15-16/01/0001")

        bill_2 = bill_1.copy({"date": "2016-01-02"})
        with Form(bill_2) as bill_2_form:
            self.assertFalse(bill_2_form.name)
            bill_2.name = "BILL/15-16/01/0002"
            self.assertMoveName(bill_2_form, "BILL/15-16/01/0001")

        bill_3 = bill_1.copy({"date": "2016-01-03"})
        bill_4 = bill_1.copy({"date": "2016-01-04"})
        (bill_3 + bill_4).date = fields.Date.from_string("2016-02-01")

        with Form(bill_3) as bill_3_form:
            self.assertMoveName(bill_3_form, "BILL/15-16/02/0001")

        with Form(bill_4) as bill_4_form:
            self.assertFalse(bill_4_form.name)
            bill_4.name = "BILL/15-16/02/0002"
            self.assertMoveName(bill_4_form, "BILL/15-16/02/0001")

    def test_sequence_draft_change_date(self):
        new_move = self.test_move.copy({"date": "2016-02-01"})
        new_multiple_move_1 = self.test_move.copy({"date": "2016-03-01"})
        new_multiple_move_2 = self.test_move.copy({"date": "2016-04-01"})
        new_moves = new_multiple_move_1 + new_multiple_move_2

        self.assertMoveName(new_move, "MISC/15-16/02/0001")
        self.assertMoveName(new_multiple_move_1, "MISC/15-16/03/0001")
        self.assertMoveName(new_multiple_move_2, "MISC/16-17/04/0001")

        self.test_move.action_post()
        new_move.date = fields.Date.to_date("2016-01-10")
        new_moves.date = fields.Date.to_date("2016-01-15")

        self.assertMoveName(new_move, False)
        self.assertMoveName(new_multiple_move_1, False)
        self.assertMoveName(new_multiple_move_2, False)

        new_move.date = fields.Date.to_date("2016-02-01")
        new_moves.date = fields.Date.to_date("2016-03-01")

        self.assertMoveName(new_move, "MISC/15-16/02/0001")
        self.assertMoveName(new_multiple_move_1, "MISC/15-16/03/0001")
        self.assertMoveName(new_multiple_move_2, "MISC/15-16/03/0001")

        new_multiple_move_1.date = fields.Date.to_date("2016-01-10")
        new_multiple_move_2.date = fields.Date.to_date("2016-02-10")

        self.assertMoveName(new_multiple_move_1, False)
        self.assertMoveName(new_multiple_move_2, "MISC/15-16/02/0001")

        journal = self.env["account.journal"].create(
            {
                "name": "awesome journal",
                "type": "general",
                "code": "AJ",
            }
        )
        new_moves.journal_id = journal

        self.assertMoveName(new_multiple_move_1, "AJ/15-16/01/0001")
        self.assertMoveName(new_multiple_move_2, "AJ/15-16/02/0001")

        with Form(new_multiple_move_1) as move_form:
            move_form.date = fields.Date.to_date("2016-01-11")
            self.assertMoveName(new_multiple_move_1, "AJ/15-16/01/0001")
            move_form.date = fields.Date.to_date("2016-01-10")

    def test_sequence_draft_change_date_with_new_sequence(self):
        invoice_1 = self.test_move.copy(
            {
                "date": "2016-02-01",
                "journal_id": self.company_data["default_journal_sale"].id,
            }
        )
        invoice_2 = invoice_1.copy({"date": "2016-02-02"})

        self.assertMoveName(invoice_2, "INV/15-16/0001")
        invoice_1.name = "INV/15-16/02/001"
        invoice_2.date = "2016-03-01"
        self.assertMoveName(invoice_2, "INV/15-16/03/001")

    def test_sequence_draft_first_of_period(self):
        move_a = self.test_move.copy({"date": "2023-02-01"})
        self.assertMoveName(move_a, "MISC/22-23/02/0001")

        move_b = self.test_move.copy({"date": "2023-02-02"})
        self.assertMoveName(move_b, "MISC/22-23/02/0001")

        move_b.action_post()
        self.assertMoveName(move_b, "MISC/22-23/02/0001")

        move_a.action_cancel()
        self.assertMoveName(move_a, False)

    def test_journal_sequence(self):
        self.assertMoveName(self.test_move, "MISC/15-16/01/0001")
        self.test_move.action_post()
        self.assertMoveName(self.test_move, "MISC/15-16/01/0001")

        copy1 = self.create_move(date=self.test_move.date)
        self.assertMoveName(copy1, False)
        copy1.action_post()
        self.assertMoveName(copy1, "MISC/15-16/01/0002")

        copy2 = self.create_move(date=self.test_move.date)
        new_journal = self.test_move.journal_id.copy()
        new_journal.code = "MISC2"
        copy2.journal_id = new_journal
        self.assertMoveName(copy2, "MISC2/15-16/01/0001")
        copy2.action_post()
        copy2.action_draft()
        with Form(copy2) as move_form:
            with self.assertLogs("odoo.tests.form") as cm:
                move_form.name = "MyMISC/2016/0001"
                self.assertTrue(
                    cm.output[0].startswith("WARNING:odoo.tests.form.onchange:")
                )
                self.assertIn(
                    "The sequence will restart at 1 at the start of every year",
                    cm.output[0],
                )

        copy2.name = False
        copy2.journal_id = self.test_move.journal_id
        self.assertMoveName(copy2, False)
        copy2.journal_id = new_journal
        self.assertMoveName(copy2, "MISC2/15-16/01/0001")

        copy2.name = "MyMISC/2016/0001"
        copy2.action_post()
        self.assertMoveName(copy2, "MyMISC/2016/0001")

        copy3 = self.create_move(date=copy2.date, journal=new_journal)
        self.assertMoveName(copy3, False)
        copy3.name = "MISC2/2016/00002"
        copy3.action_post()

        copy4 = self.create_move(date=copy2.date, journal=new_journal)
        copy4.action_post()
        self.assertMoveName(copy4, "MISC2/2016/00003")

        copy5 = self.create_move(date=copy2.date, journal=new_journal)
        copy5.date = "2021-02-02"
        copy5.action_post()
        self.assertMoveName(copy5, "MISC2/2021/00001")
        copy5.name = "N'importe quoi?"

        copy6 = self.create_move(date=copy5.date, journal=new_journal)
        copy6.action_post()
        self.assertMoveName(copy6, "N'importe quoi?1")

    def test_journal_sequence_format(self):
        sequences = [
            (
                "JRNL/2016/00001",
                "JRNL/2016/00002",
                "JRNL/2016/00003",
                "JRNL/2017/00001",
            ),
            (
                "JRNL/2015-2016/00001",
                "JRNL/2015-2016/00002",
                "JRNL/2016-2017/00001",
                "JRNL/2016-2017/00002",
            ),
            (
                "JRNL/2015-16/00001",
                "JRNL/2015-16/00002",
                "JRNL/2016-17/00001",
                "JRNL/2016-17/00002",
            ),
            (
                "JRNL/15-16/00001",
                "JRNL/15-16/00002",
                "JRNL/16-17/00001",
                "JRNL/16-17/00002",
            ),
            ("1234567", "1234568", "1234569", "1234570"),
            ("20190910", "20190911", "20190912", "20190913"),
            ("2016-0910", "2016-0911", "2016-0912", "2017-0001"),
            ("201603-10", "201603-11", "201604-01", "201703-01"),
            ("16-03-10", "16-03-11", "16-04-01", "17-03-01"),
            ("2016-10", "2016-11", "2016-12", "2017-01"),
            ("045-001-000002", "045-001-000003", "045-001-000004", "045-001-000005"),
            (
                "JRNL/2016/00001suffix",
                "JRNL/2016/00002suffix",
                "JRNL/2016/00003suffix",
                "JRNL/2017/00001suffix",
            ),
        ]

        init_move = self.create_move(date="2016-03-12")
        next_move = self.create_move(date="2016-03-12")
        next_move_month = self.create_move(date="2016-04-12")
        next_move_year = self.create_move(date="2017-03-12")
        next_moves = next_move + next_move_month + next_move_year
        next_moves.action_post()

        for (
            sequence_init,
            sequence_next,
            sequence_next_month,
            sequence_next_year,
        ) in sequences:
            init_move.name = sequence_init
            next_moves.name = False
            next_moves._compute_name()
            self.assertEqual(
                [next_move.name, next_move_month.name, next_move_year.name],
                [sequence_next, sequence_next_month, sequence_next_year],
            )

    def test_journal_next_sequence(self):
        prefix = "TEST_ORDER/2016/"
        self.test_move.name = f"{prefix}1"
        for c in range(2, 25):
            copy = self.create_move(date=self.test_move.date)
            copy.name = False
            copy.action_post()
            self.assertMoveName(copy, f"{prefix}{c}")

    def test_journal_sequence_multiple_type(self):
        entry, entry2, invoice, invoice2, refund, refund2 = (
            self.create_move(date="2016-01-01") for i in range(6)
        )
        (invoice + invoice2 + refund + refund2).write(
            {
                "journal_id": self.company_data["default_journal_sale"].id,
                "partner_id": 1,
                "invoice_date": "2016-01-01",
            }
        )
        (invoice + invoice2).move_type = "out_invoice"
        (refund + refund2).move_type = "out_refund"
        all_moves = entry + entry2 + invoice + invoice2 + refund + refund2
        all_moves.name = False
        all_moves.action_post()
        self.assertEqual(entry.name, "MISC/15-16/01/0001")
        self.assertEqual(entry2.name, "MISC/15-16/01/0002")
        self.assertEqual(invoice.name, "INV/15-16/0001")
        self.assertEqual(invoice2.name, "INV/15-16/0002")
        self.assertEqual(refund.name, "RINV/15-16/0001")
        self.assertEqual(refund2.name, "RINV/15-16/0002")

    def test_journal_sequence_groupby_compute(self):
        journals = self.env["account.journal"].create(
            [
                {
                    "name": f"Journal{i}",
                    "code": f"J{i}",
                    "type": "general",
                }
                for i in range(2)
            ]
        )
        account = self.env["account.account"].search([], limit=1)
        moves = (
            self.env["account.move"]
            .create(
                [
                    {
                        "journal_id": journals[i].id,
                        "line_ids": [
                            (0, 0, {"account_id": account.id, "name": "line"})
                        ],
                        "date": "2010-01-01",
                    }
                    for i in range(2)
                ]
            )
            ._post()
        )
        for i in range(2):
            moves[i].name = f"J{i}/2010/00001"

        moves = (
            self.env["account.move"]
            .create(
                [
                    {
                        "journal_id": journals[journal_index].id,
                        "line_ids": [
                            (0, 0, {"account_id": account.id, "name": "line"})
                        ],
                        "date": f"2010-{month:02d}-01",
                    }
                    for journal_index, month in [(1, 1), (0, 1), (1, 2), (1, 1)]
                ]
            )
            ._post()
        )
        self.assertEqual(
            moves.mapped("name"),
            ["J1/2010/00002", "J0/2010/00002", "J1/2010/00004", "J1/2010/00003"],
        )

        journals[0].code = "OLD"
        journals.flush_recordset()
        journal_same_code = self.env["account.journal"].create(
            [
                {
                    "name": "Journal0",
                    "code": "J0",
                    "type": "general",
                }
            ]
        )
        moves = (
            self.create_move(
                date="2010-01-01", journal=journal_same_code, name="J0/2010/00001"
            )
            + self.create_move(date="2010-01-01", journal=journal_same_code)
            + self.create_move(date="2010-01-01", journal=journal_same_code)
            + self.create_move(date="2010-01-01", journal=journals[0])
        )._post()
        self.assertEqual(
            moves.mapped("name"),
            ["J0/2010/00001", "J0/2010/00002", "J0/2010/00003", "J0/2010/00003"],
        )

    def test_journal_override_sequence_regex(self):
        self.create_move(date="2020-01-01", name="00000876-G 0002/2020")
        next_move = self.create_move(date="2020-01-01")
        next_move.action_post()
        self.assertMoveName(next_move, "00000876-G 0002/2021")

        next_move.action_draft()
        next_move.name = False
        next_move.journal_id.sequence_override_regex = (
            r"^(?P<seq>\d*)(?P<suffix1>.*?)(?P<year>(\d{4})?)(?P<suffix2>)$"
        )
        next_move.action_post()
        self.assertMoveName(next_move, "00000877-G 0002/2020")
        next_move = self.create_move(date="2020-01-01")
        next_move.action_post()
        self.assertMoveName(next_move, "00000878-G 0002/2020")

        next_move = self.create_move(date="2017-05-02")
        next_move.action_post()
        self.assertMoveName(next_move, "00000001-G 0002/2017")

    def test_journal_override_sequence_regex_year(self):
        move = self.create_move(date="2020-01-01")
        move.journal_id.sequence_override_regex = (
            "^"
            r"(?P<prefix1>.*?)"
            r"(?P<year>(?:(?<=\D)|(?<=^))\d{4})?"
            r"(?P<prefix2>(?<=\d{4}).*?)?"
            r"(?P<seq>\d{0,9})"
            r"(?P<suffix>\D*?)"
            "$"
        )

        next_move = self.create_move(date="2020-01-01", name="MISC/2020/21/00001")
        next_move.action_post()
        self.assertEqual(next_move.name, "MISC/2020/21/00001")

        next_move = self.create_move(date="2020-01-01")
        next_move.action_post()
        self.assertEqual(next_move.name, "MISC/2020/21/00002")

        next_move = self.create_move(date="2021-01-01")
        next_move.action_post()
        self.assertEqual(next_move.name, "MISC/2021/21/00001")

        with self.assertRaises(ValidationError):
            self.create_move(date="2022-01-01", name="MISC/2021/22/00001", post=True)
        self.create_move(date="2022-01-01", name="MISC/2022/22/00001", post=True)

    def test_journal_sequence_ordering(self):
        self.test_move.name = "XMISC/2016/00001"
        copies = reduce(
            (lambda x, y: x + y),
            [self.create_move(date=self.test_move.date) for i in range(6)],
        )

        copies[0].date = "2019-03-05"
        copies[1].date = "2019-03-06"
        copies[2].date = "2019-03-07"
        copies[3].date = "2019-03-04"
        copies[4].date = "2019-03-05"
        copies[5].date = "2019-03-05"
        copies[0].name = False
        copies.action_post()

        self.assertMoveName(copies[0], "XMISC/2019/00002")
        self.assertMoveName(copies[1], "XMISC/2019/00005")
        self.assertMoveName(copies[2], "XMISC/2019/00006")
        self.assertMoveName(copies[3], "XMISC/2019/00001")
        self.assertMoveName(copies[4], "XMISC/2019/00003")
        self.assertMoveName(copies[5], "XMISC/2019/00004")

        with self.assertRaises(psycopg.DatabaseError), mute_logger("odoo.db"):
            copies[0].name = "XMISC/2019/00001"

        copies[0].name = "XMISC/2019/10001"
        copies[1].name = "XMISC/2019/10002"
        copies[2].name = "XMISC/2019/10003"
        copies[3].name = "XMISC/2019/10004"
        copies[4].name = "XMISC/2019/10005"
        copies[5].name = "XMISC/2019/10006"

        copies[4].action_draft()
        copies[4].with_context(force_delete=True).unlink()
        copies[5].action_draft()

        wizard = Form(
            self.env["account.resequence.wizard"].with_context(
                active_ids=set(copies.ids) - set(copies[4].ids),
                active_model="account.move",
            ),
        )

        new_values = json.loads(wizard.new_values)
        self.assertEqual(
            new_values[str(copies[0].id)]["new_by_date"], "XMISC/2019/10002"
        )
        self.assertEqual(
            new_values[str(copies[0].id)]["new_by_name"], "XMISC/2019/10001"
        )

        self.assertEqual(
            new_values[str(copies[1].id)]["new_by_date"], "XMISC/2019/10004"
        )
        self.assertEqual(
            new_values[str(copies[1].id)]["new_by_name"], "XMISC/2019/10002"
        )

        self.assertEqual(
            new_values[str(copies[2].id)]["new_by_date"], "XMISC/2019/10005"
        )
        self.assertEqual(
            new_values[str(copies[2].id)]["new_by_name"], "XMISC/2019/10003"
        )

        self.assertEqual(
            new_values[str(copies[3].id)]["new_by_date"], "XMISC/2019/10001"
        )
        self.assertEqual(
            new_values[str(copies[3].id)]["new_by_name"], "XMISC/2019/10004"
        )

        self.assertEqual(
            new_values[str(copies[5].id)]["new_by_date"], "XMISC/2019/10003"
        )
        self.assertEqual(
            new_values[str(copies[5].id)]["new_by_name"], "XMISC/2019/10005"
        )

        wizard.save().resequence()

        self.assertEqual(copies[3].state, "posted")
        self.assertMoveName(copies[5], "XMISC/2019/10005")
        self.assertEqual(copies[5].state, "draft")

    def test_journal_resequence_in_between_2_years_pattern(self):
        self.test_move.name = "XMISC/2015-2016/00001"
        invoices = (
            self.create_move(date="2023-03-01", post=True)
            + self.create_move(date="2023-03-02", post=True)
            + self.create_move(date="2023-03-03", post=True)
            + self.create_move(date="2023-04-01", post=True)
            + self.create_move(date="2023-04-02", post=True)
        )
        self.assertRecordValues(
            invoices,
            (
                {"name": "XMISC/2022-2023/00001", "state": "posted"},
                {"name": "XMISC/2022-2023/00002", "state": "posted"},
                {"name": "XMISC/2022-2023/00003", "state": "posted"},
                {"name": "XMISC/2023-2024/00001", "state": "posted"},
                {"name": "XMISC/2023-2024/00002", "state": "posted"},
            ),
        )

        resequence_wizard = Form(
            self.env["account.resequence.wizard"].with_context(
                active_ids=invoices.ids, active_model="account.move"
            )
        )
        resequence_wizard.first_name = "XMISC/22-23/00001"
        new_values = json.loads(resequence_wizard.new_values)
        self.assertEqual(
            new_values[str(invoices[0].id)]["new_by_name"], "XMISC/22-23/00001"
        )
        self.assertEqual(
            new_values[str(invoices[1].id)]["new_by_name"], "XMISC/22-23/00002"
        )
        self.assertEqual(
            new_values[str(invoices[2].id)]["new_by_name"], "XMISC/22-23/00003"
        )
        self.assertEqual(
            new_values[str(invoices[3].id)]["new_by_name"], "XMISC/23-24/00001"
        )
        self.assertEqual(
            new_values[str(invoices[4].id)]["new_by_name"], "XMISC/23-24/00002"
        )
        resequence_wizard.save().resequence()

        self.assertRecordValues(
            invoices,
            (
                {"name": "XMISC/22-23/00001", "state": "posted"},
                {"name": "XMISC/22-23/00002", "state": "posted"},
                {"name": "XMISC/22-23/00003", "state": "posted"},
                {"name": "XMISC/23-24/00001", "state": "posted"},
                {"name": "XMISC/23-24/00002", "state": "posted"},
            ),
        )

    def test_sequence_staggered_year(self):
        self.env.company.account_config_id.quick_edit_mode = "out_and_in_invoices"
        self.env.company.account_config_id.fiscalyear_last_day = 15
        self.env.company.account_config_id.fiscalyear_last_month = "4"

        bill = self.env["account.move"].create(
            {
                "partner_id": 1,
                "move_type": "in_invoice",
                "date": "2024-04-17",
                "line_ids": [
                    Command.create(
                        {
                            "name": "line",
                            "account_id": self.company_data[
                                "default_account_revenue"
                            ].id,
                        }
                    ),
                ],
            }
        )
        self.assertMoveName(bill, "BILL/24-25/04/0001")
        bill_copy = bill.copy({"date": "2024-04-10", "invoice_date": "2024-04-10"})
        bill_copy.action_post()
        self.assertMoveName(bill_copy, "BILL/23-24/04/0001")
        bill_copy_2 = bill.copy({"date": "2024-04-11", "invoice_date": "2024-04-11"})
        bill_copy_2.action_post()
        self.assertMoveName(bill_copy_2, "BILL/23-24/04/0002")
        bill_copy_3 = bill.copy({"date": "2024-04-18", "invoice_date": "2024-04-18"})
        bill_copy_3.action_post()
        self.assertMoveName(bill_copy_3, "BILL/24-25/04/0001")

    def test_sequence_get_more_specific(self):
        self.test_move.name = "MISC/00001"

        new_year = self.set_sequence(
            self.test_move.date + relativedelta(years=1), "MISC/2017/00001"
        )

        new_month = self.set_sequence(
            new_year.date + relativedelta(months=1), "MISC/2017/02/00001"
        )

        self.assertNameAtDate(self.test_move.date, "MISC/00002")
        self.assertNameAtDate(new_year.date, "MISC/2017/00002")
        self.assertNameAtDate(new_month.date, "MISC/2017/02/00002")

        start_fiscal = self.set_sequence(
            new_year.date + relativedelta(months=2), "MISC/2016-2017/00001"
        )

        self.assertNameAtDate(self.test_move.date, "MISC/00003")
        self.assertNameAtDate(new_year.date, "MISC/2016-2017/00002")
        self.assertNameAtDate(new_month.date, "MISC/2017/02/00003")
        self.assertNameAtDate(start_fiscal.date, "MISC/2016-2017/00003")

        reset_never = self.set_sequence(
            self.test_move.date + relativedelta(years=2), "MISC/00100"
        )
        self.assertNameAtDate(reset_never.date, "MISC/00101")

    def test_fiscal_vs_monthly(self):
        self.set_sequence("2101-02-01", "MISC/01-02/00001")
        move = self.assertNameAtDate("2101-03-01", "MISC/01-03/00001")

        move.journal_id.sequence_override_regex = move._sequence_year_range_regex
        move.name = "MISC/00-01/00001"
        self.assertNameAtDate("2101-03-01", "MISC/00-01/00002")

    def test_resequence_clash(self):
        moves = self.env["account.move"]
        for i in range(3):
            moves += self.create_move(name=str(i))
        moves.action_post()

        mistake = moves[1]
        mistake.action_draft()
        mistake.posted_before = False
        mistake.with_context(force_delete=True).unlink()
        moves -= mistake

        self.env["account.resequence.wizard"].create(
            {
                "move_ids": moves.ids,
                "first_name": "2",
            }
        ).resequence()

    @freeze_time("2021-10-01 00:00:00")
    def test_change_journal_on_first_account_move(self):
        journal = self.env["account.journal"].create(
            {
                "name": "awesome journal",
                "type": "general",
                "code": "AJ",
            }
        )
        move = self.env["account.move"].create({})
        self.assertMoveName(move, "MISC/21-22/10/0001")
        with Form(move) as move_form:
            move_form.journal_id = journal
        self.assertMoveName(move, "AJ/21-22/10/0001")

    def test_sequence_move_name_related_field_well_computed(self):
        AccountMove = type(self.env["account.move"])
        _compute_name = AccountMove._compute_name

        def _flushing_compute_name(self):
            self.env["account.move.line"].flush_model(fnames=["move_name"])
            _compute_name(self)

        payments = self.env["account.payment"].create(
            [
                {
                    "payment_type": "inbound",
                    "payment_method_id": self.env.ref(
                        "account.account_payment_method_manual_in"
                    ).id,
                    "partner_type": "customer",
                    "partner_id": self.partner_a.id,
                    "amount": 500,
                }
            ]
            * 2
        )

        with patch.object(AccountMove, "_compute_name", _flushing_compute_name):
            payments.action_post()

        for move in payments.move_id:
            self.assertRecordValues(
                move.line_ids, [{"move_name": move.name}] * len(move.line_ids)
            )
            self.assertRecordValues(
                move.line_ids, [{"name": "Manual Payment"}] * len(move.line_ids)
            )

    def test_resequence_payment_and_non_payment_without_payment_sequence(self):
        journal = self.company_data["default_journal_bank"].copy(
            {"payment_sequence": False}
        )
        bsl = self.env["account.bank.statement.line"].create(
            {"name": "test", "amount": 100, "journal_id": journal.id}
        )
        payment = self.env["account.payment"].create(
            {
                "payment_type": "inbound",
                "partner_id": self.partner_a.id,
                "amount": 100,
                "journal_id": journal.id,
            }
        )

        payment.action_post()
        wizard = Form(
            self.env["account.resequence.wizard"].with_context(
                active_ids=(payment.move_id + bsl.move_id).ids,
                active_model="account.move",
            ),
        )

        wizard.save().resequence()
        self.assertTrue(wizard)

    def test_change_same_journal_not_change_sequence(self):
        self.create_move(date="2025-10-17", post=True)
        move2 = self.create_move(date="2025-10-17", post=True)
        self.create_move(date="2025-10-17", post=True)
        move2.journal_id = move2.journal_id
        self.assertEqual(move2.name, "MISC/25-26/10/0002")

    def test_limit_savepoint(self):
        with patch.object(
            self.env.cr, "savepoint", Mock(wraps=self.env.cr.savepoint)
        ) as mock:
            self.create_move(date="2020-01-01", post=True)
        mock.assert_called_once()
        with patch.object(
            self.env.cr, "savepoint", Mock(wraps=self.env.cr.savepoint)
        ) as mock:
            self.create_move(date="2020-01-01", post=True)
        mock.assert_not_called()
        with patch.object(
            self.env.cr, "savepoint", Mock(wraps=self.env.cr.savepoint)
        ) as mock:
            self.create_move(date="2021-01-01", post=True)
        mock.assert_called_once()

    def test_init_recreates_dropped_secondary_index(self):
        move = self.env["account.move"]
        idx2 = move._table + "_sequence_index2"

        def index_present():
            self.env.cr.execute(
                "SELECT 1 FROM pg_indexes WHERE indexname = %s", (idx2,)
            )
            return bool(self.env.cr.fetchone())

        self.env.cr.execute(f'DROP INDEX IF EXISTS "{idx2}"')
        self.assertFalse(index_present(), "precondition: secondary index dropped")
        move.init()
        self.assertTrue(
            index_present(), "init() must recreate the dropped secondary index"
        )

    def test_new_sequence_requires_date(self):
        move = self.create_move(date="2099-12-01")
        move.name = False
        move.date = False
        with self.assertRaisesRegex(
            ValidationError, "required to start a new sequence"
        ):
            move._get_next_sequence_format()

    def test_sequence_format_param_roundtrip(self):
        move = self.env["account.move"]
        cases = {
            "MISC/2042/00123": "year",
            "MISC/2042-2043/00123": "year_range",
            "MISC/2019/04/0001": "month",
            "MISC/2042-2043/04/000123": "year_range_month",
            "MISC/00123": "never",
            "2019/00001": "year",
            "INV/2019/0001": "year",
            "PAY/19-20/0007": "year_range",
            "0000000001": "never",
            "MISC/15-16/01/0001": "year_range_month",
            "BILL/15-16/0001": "year_range",
            "ABC123": "never",
            "XYZ/2021-2022/12/9999": "year_range_month",
        }
        for name, expected_reset in cases.items():
            with self.subTest(name=name):
                self.assertEqual(
                    move._deduce_sequence_number_reset(name),
                    expected_reset,
                    f"wrong reset deduced for {name!r}",
                )
                fmt, values = move._get_sequence_format_param(name)
                self.assertEqual(
                    fmt.format(**values),
                    name,
                    f"round-trip failed for {name!r}",
                )


@tagged("post_install", "-at_install")
class TestSequenceGaps(TestSequenceMixinCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        move_1 = cls.create_move()
        move_2 = cls.create_move()
        move_3 = cls.create_move()
        all_moves = move_1 + move_2 + move_3
        all_moves.action_post()
        cls.all_moves = all_moves

    def test_basic(self):
        self.assertEqual(
            self.all_moves.mapped("made_sequence_gap"), [False, False, False]
        )

    def test_first(self):
        new_move = self.create_move(name="NEW/000001")
        new_move.action_post()
        self.assertEqual(new_move.made_sequence_gap, False)

    def test_unlink(self):
        self.all_moves[0].action_draft()
        self.all_moves[0].unlink()
        self.assertEqual(
            self.all_moves.exists().mapped("made_sequence_gap"), [True, False]
        )
        self.all_moves[1].action_draft()
        self.all_moves[1].unlink()
        self.assertEqual(self.all_moves.exists().mapped("made_sequence_gap"), [True])

    def test_unlink_2(self):
        self.all_moves[1].action_draft()
        self.all_moves[1].unlink()
        self.assertEqual(
            self.all_moves.exists().mapped("made_sequence_gap"), [False, True]
        )
        self.all_moves[0].action_draft()
        self.all_moves[0].unlink()
        self.assertEqual(self.all_moves.exists().mapped("made_sequence_gap"), [True])

    def test_change_sequence(self):
        previous = self.all_moves[1].name
        self.all_moves[1].name = "/"
        self.assertEqual(
            self.all_moves.mapped("made_sequence_gap"), [False, False, True]
        )
        self.all_moves[1].name = previous
        self.assertEqual(
            self.all_moves.mapped("made_sequence_gap"), [False, False, False]
        )

    def test_change_multi(self):
        self.all_moves[0].name = "/"
        self.all_moves[1].name = "/"
        self.assertEqual(
            self.all_moves.mapped("made_sequence_gap"), [False, False, True]
        )

    def test_change_multi_2(self):
        self.all_moves[1].name = "/"
        self.all_moves[0].name = "/"
        self.assertEqual(
            self.all_moves.mapped("made_sequence_gap"), [False, False, True]
        )

    def test_null_change(self):
        self.all_moves[1].name = self.all_moves[1].name
        self.assertEqual(
            self.all_moves.mapped("made_sequence_gap"), [False, False, False]
        )

    def test_create_fill_gap(self):
        previous = self.all_moves[1].name
        self.all_moves[1].action_draft()
        self.all_moves[1].unlink()
        self.assertEqual(
            self.all_moves.exists().mapped("made_sequence_gap"), [False, True]
        )
        new_move = self.create_move(name=previous)
        self.assertEqual(
            self.all_moves.exists().mapped("made_sequence_gap"), [False, False]
        )
        self.assertEqual(new_move.made_sequence_gap, True)
        new_move.action_post()
        self.assertEqual(new_move.made_sequence_gap, False)

    def test_create_gap(self):
        last = self.all_moves[2].name
        format_string, format_values = self.all_moves[0]._get_sequence_format_param(
            last
        )
        format_values["seq"] += 10
        new_move = self.create_move(name=format_string.format(**format_values))
        new_move.action_post()
        self.assertEqual(new_move.made_sequence_gap, True)


@tagged("post_install", "-at_install")
class TestSequenceMixinDeletion(TestSequenceMixinCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        journal = cls.env["account.journal"].create(
            {
                "name": "Test sequences - deletion",
                "code": "SEQDEL",
                "type": "general",
            }
        )

        cls.move_1_1 = cls.create_move(
            "2021-01-01", journal, name="TOTO/2021/01/0001", post=True
        )
        cls.move_1_2 = cls.create_move("2021-01-02", journal, post=True)
        cls.move_1_3 = cls.create_move("2021-01-03", journal, post=True)
        cls.move_2_1 = cls.create_move("2021-02-01", journal, post=True)
        cls.move_draft = cls.create_move("2021-02-02", journal, post=False)
        cls.move_2_2 = cls.create_move("2021-02-03", journal, post=True)
        cls.move_3_1 = cls.create_move(
            "2021-02-10", journal, name="TURLUTUTU/21/02/001", post=True
        )

    def test_sequence_deletion_1(self):
        self.move_draft.unlink()

        for move in (
            self.move_1_3,
            self.move_1_2,
            self.move_3_1,
            self.move_2_2,
            self.move_2_1,
            self.move_1_1,
        ):
            move.action_draft()
            move.unlink()

    def test_sequence_deletion_2(self):
        all_moves = (
            self.move_1_3
            + self.move_1_2
            + self.move_3_1
            + self.move_2_2
            + self.move_2_1
            + self.move_1_1
        )
        all_moves.action_draft()
        all_moves.unlink()

    def test_sequence_chain_with_null_prefix(self):
        move = self.move_1_2
        self.env.cr.execute(
            "UPDATE account_move SET sequence_prefix = NULL WHERE id = %s",
            (move.id,),
        )
        move.invalidate_recordset(["sequence_prefix"])
        self.assertIs(
            move.sequence_prefix, False, "A NULL Char must read back as False"
        )
        self.assertIsInstance(move.check_move_sequence_chain(), bool)


@tagged("post_install", "-at_install")
class TestSequenceMixinConcurrency(TransactionCase):
    def setUp(self):
        super().setUp()
        with self.env.registry.cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            journal = env["account.journal"].create(
                {
                    "name": "concurency_test",
                    "code": "CT",
                    "type": "general",
                }
            )
            account = env["account.account"].create(
                {
                    "code": "CT",
                    "name": "CT",
                    "account_type": "asset_fixed",
                }
            )
            moves = env["account.move"].create(
                [
                    {
                        "journal_id": journal.id,
                        "date": fields.Date.from_string("2016-01-01"),
                        "line_ids": [
                            (0, 0, {"name": "name", "account_id": account.id})
                        ],
                    }
                ]
                * 3
            )
            moves.name = False
            moves[0].action_post()
            self.assertEqual(moves.mapped("name"), ["CT/2016/01/0001", False, False])
            env.cr.commit()
        self.data = {
            "move_ids": moves.ids,
            "account_id": account.id,
            "journal_id": journal.id,
            "envs": [
                api.Environment(self.env.registry.cursor(), SUPERUSER_ID, {}),
                api.Environment(self.env.registry.cursor(), SUPERUSER_ID, {}),
                api.Environment(self.env.registry.cursor(), SUPERUSER_ID, {}),
            ],
        }
        self.addCleanup(self.cleanUp)

    def cleanUp(self):
        with self.env.registry.cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            moves = env["account.move"].browse(self.data["move_ids"])
            moves.filtered(lambda x: x.state in ("posted", "cancel")).action_draft()
            moves.posted_before = False
            moves.unlink()
            journal = env["account.journal"].browse(self.data["journal_id"])
            journal.unlink()
            account = env["account.account"].browse(self.data["account_id"])
            account.unlink()
            env.cr.commit()
        for env in self.data["envs"]:
            env.cr.close()

    def test_sequence_concurency(self):
        env0, env1, env2 = self.data["envs"]

        env1.cr.execute("SELECT 1")

        move = env2["account.move"].browse(self.data["move_ids"][1])
        move.action_post()
        env2.cr.commit()

        move = env1["account.move"].browse(self.data["move_ids"][2])
        move.action_post()
        env1.cr.commit()

        moves = env0["account.move"].browse(self.data["move_ids"])
        self.assertEqual(
            moves.mapped("name"),
            ["CT/2016/01/0001", "CT/2016/01/0002", "CT/2016/01/0003"],
        )
        self.assertEqual(
            moves.mapped("sequence_prefix"),
            ["CT/2016/01/", "CT/2016/01/", "CT/2016/01/"],
        )
        self.assertEqual(moves.mapped("sequence_number"), [1, 2, 3])
        self.assertEqual(moves.mapped("made_sequence_gap"), [False, False, False])
        for line in moves.line_ids:
            self.assertEqual(line.move_name, line.move_id.name)

    def test_sequence_concurency_no_useless_lock(self):
        env0, env1, env2 = self.data["envs"]

        env1.cr.execute("SELECT 1")

        move = env2["account.move"].browse(self.data["move_ids"][1])
        _ = move.highest_name
        env2.cr.commit()

        move = env1["account.move"].browse(self.data["move_ids"][2])
        move.action_post()
        env1.cr.commit()

        moves = env0["account.move"].browse(self.data["move_ids"])
        self.assertEqual(
            moves.mapped("name"), ["CT/2016/01/0001", False, "CT/2016/01/0002"]
        )
