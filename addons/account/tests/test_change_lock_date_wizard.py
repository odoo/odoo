from contextlib import closing
from datetime import timedelta

from odoo import fields
from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tools import frozendict

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.account.wizards.account_change_lock_date import (
    SOFT_LOCK_DATE_FIELDS,
)


@tagged("post_install", "-at_install")
class TestChangeLockDateWizard(AccountTestInvoicingCommon):
    def test_exception_generation(self):
        self.env["account.lock_exception"].search([]).sudo().unlink()

        for lock_date_field in SOFT_LOCK_DATE_FIELDS:
            with (
                self.subTest(lock_date_field=lock_date_field),
                closing(self.cr.savepoint()),
            ):
                self.env["account.change.lock.date"].create(
                    {lock_date_field: "2010-01-01"}
                ).change_lock_date()
                self.assertEqual(
                    self.env.company.account_config_id[lock_date_field],
                    fields.Date.from_string("2010-01-01"),
                )

                self.env["account.change.lock.date"].create(
                    {lock_date_field: "2011-01-01"}
                ).change_lock_date()
                self.assertEqual(
                    self.env.company.account_config_id[lock_date_field],
                    fields.Date.from_string("2011-01-01"),
                )

                wizard = self.env["account.change.lock.date"].create(
                    {
                        lock_date_field: False,
                        "exception_applies_to": "everyone",
                        "exception_duration": "1h",
                        "exception_reason": ":TestChangeLockDateWizard.test_exception_generation; remove",
                    }
                )
                wizard.change_lock_date()
                self.assertEqual(self.env["account.lock_exception"].search_count([]), 1)
                exception = self.env["account.lock_exception"].search([])
                self.assertEqual(len(exception), 1)
                self.assertRecordValues(
                    exception,
                    [
                        {
                            lock_date_field: False,
                            "company_id": self.env.company.id,
                            "user_id": False,
                            "create_uid": self.env.user.id,
                            "end_datetime": self.env.cr.now() + timedelta(hours=1),
                            "reason": ":TestChangeLockDateWizard.test_exception_generation; remove",
                        }
                    ],
                )
                exception.sudo().unlink()

                self.assertEqual(self.env["account.lock_exception"].search_count([]), 0)

                self.env["account.change.lock.date"].create(
                    {lock_date_field: "2009-01-01"}
                ).change_lock_date()
                self.assertEqual(
                    self.env.company.account_config_id[lock_date_field],
                    fields.Date.from_string("2011-01-01"),
                )
                exception = self.env["account.lock_exception"].search([])
                self.assertEqual(len(exception), 1)
                self.assertRecordValues(
                    exception,
                    [
                        {
                            lock_date_field: fields.Date.from_string("2009-01-01"),
                            "company_id": self.env.company.id,
                            "user_id": self.env.user.id,
                            "create_uid": self.env.user.id,
                            "end_datetime": self.env.cr.now() + timedelta(minutes=5),
                            "reason": False,
                        }
                    ],
                )

    def test_exception_generation_multiple(self):
        self.env["account.lock_exception"].search([]).sudo().unlink()

        wizard = self.env["account.change.lock.date"].create(
            {
                "fiscalyear_lock_date": "2010-01-01",
                "tax_lock_date": "2010-01-01",
                "sale_lock_date": "2010-01-01",
                "purchase_lock_date": "2010-01-01",
            }
        )
        wizard.change_lock_date()

        self.assertRecordValues(
            self.env.company.account_config_id,
            [
                {
                    "fiscalyear_lock_date": fields.Date.from_string("2010-01-01"),
                    "tax_lock_date": fields.Date.from_string("2010-01-01"),
                    "sale_lock_date": fields.Date.from_string("2010-01-01"),
                    "purchase_lock_date": fields.Date.from_string("2010-01-01"),
                }
            ],
        )

        wizard = self.env["account.change.lock.date"].create(
            {
                "fiscalyear_lock_date": "2009-01-01",
                "tax_lock_date": "2009-01-01",
                "sale_lock_date": "2009-01-01",
                "purchase_lock_date": "2009-01-01",
                "exception_applies_to": "everyone",
                "exception_duration": "1h",
                "exception_reason": ":TestChangeLockDateWizard.test_exception_generation; remove",
            }
        )
        wizard.change_lock_date()

        exceptions = self.env["account.lock_exception"].search([])
        self.assertEqual(len(exceptions), 4)
        expected_exceptions = {
            frozendict(
                {
                    "lock_date_field": "fiscalyear_lock_date",
                    "lock_date": fields.Date.from_string("2009-01-01"),
                }
            ),
            frozendict(
                {
                    "lock_date_field": "tax_lock_date",
                    "lock_date": fields.Date.from_string("2009-01-01"),
                }
            ),
            frozendict(
                {
                    "lock_date_field": "sale_lock_date",
                    "lock_date": fields.Date.from_string("2009-01-01"),
                }
            ),
            frozendict(
                {
                    "lock_date_field": "purchase_lock_date",
                    "lock_date": fields.Date.from_string("2009-01-01"),
                }
            ),
        }
        created_exceptions = {
            frozendict(
                {
                    "lock_date_field": exception.lock_date_field,
                    "lock_date": exception.lock_date,
                }
            )
            for exception in exceptions
        }
        self.assertSetEqual(created_exceptions, expected_exceptions)

    def test_hard_lock_date(self):
        self.env["account.lock_exception"].search([]).sudo().unlink()

        self.env["account.change.lock.date"].create(
            {"hard_lock_date": "2010-01-01"}
        ).change_lock_date()
        self.assertEqual(
            self.env.company.account_config_id.hard_lock_date,
            fields.Date.from_string("2010-01-01"),
        )

        self.env["account.change.lock.date"].create(
            {"hard_lock_date": "2011-01-01"}
        ).change_lock_date()
        self.assertEqual(
            self.env.company.account_config_id.hard_lock_date,
            fields.Date.from_string("2011-01-01"),
        )

        wizard = self.env["account.change.lock.date"].create(
            {
                "hard_lock_date": "2009-01-01",
                "exception_applies_to": "everyone",
                "exception_duration": "1h",
                "exception_reason": ":TestChangeLockDateWizard.test_hard_lock_date",
            }
        )
        with self.assertRaises(UserError):
            wizard.change_lock_date()
        self.assertEqual(
            self.env.company.account_config_id.hard_lock_date,
            fields.Date.from_string("2011-01-01"),
        )

        wizard = self.env["account.change.lock.date"].create(
            {
                "hard_lock_date": False,
                "exception_applies_to": "everyone",
                "exception_duration": "1h",
                "exception_reason": ":TestChangeLockDateWizard.test_hard_lock_date",
            }
        )
        with self.assertRaises(UserError):
            wizard.change_lock_date()
        self.assertEqual(
            self.env.company.account_config_id.hard_lock_date,
            fields.Date.from_string("2011-01-01"),
        )

        self.assertEqual(self.env["account.lock_exception"].search_count([]), 0)

    def test_everyone_forever_exception(self):
        self.env["account.lock_exception"].search([]).sudo().unlink()

        for lock_date_field in SOFT_LOCK_DATE_FIELDS:
            with (
                self.subTest(lock_date_field=lock_date_field),
                closing(self.cr.savepoint()),
            ):
                self.env["account.change.lock.date"].create(
                    {lock_date_field: "2010-01-01"}
                ).change_lock_date()
                self.assertEqual(
                    self.env.company.account_config_id[lock_date_field],
                    fields.Date.from_string("2010-01-01"),
                )

                self.env["account.change.lock.date"].create(
                    {
                        lock_date_field: "2009-01-01",
                        "exception_applies_to": "everyone",
                        "exception_duration": "forever",
                        "exception_reason": ":TestChangeLockDateWizard.test_everyone_forever_exception; remove",
                    }
                ).change_lock_date()
                self.assertEqual(
                    self.env.company.account_config_id[lock_date_field],
                    fields.Date.from_string("2009-01-01"),
                )

                self.env["account.change.lock.date"].create(
                    {
                        lock_date_field: False,
                        "exception_applies_to": "everyone",
                        "exception_duration": "forever",
                        "exception_reason": ":TestChangeLockDateWizard.test_everyone_forever_exception; remove",
                    }
                ).change_lock_date()
                self.assertEqual(
                    self.env.company.account_config_id[lock_date_field], False
                )

                self.assertEqual(self.env["account.lock_exception"].search_count([]), 0)
