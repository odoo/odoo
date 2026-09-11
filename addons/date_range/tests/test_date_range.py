# Copyright 2016 ACSONE SA/NV (<http://acsone.eu>)
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl)

import datetime

from odoo.exceptions import UserError, ValidationError
from odoo.tests.common import TransactionCase


class DateRangeTest(TransactionCase):
    def setUp(self):
        super(DateRangeTest, self).setUp()
        self.date_range = self.env["date.range"]
        self.type = self.env["date.range.type"].create(
            {"name": "Fiscal year", "company_id": False, "allow_overlap": False}
        )

        self.company = self.env["res.company"].create({"name": "Test company"})
        self.company_2 = self.env["res.company"].create(
            {"name": "Test company 2", "parent_id": self.company.id}
        )
        self.typeB = self.env["date.range.type"].create(
            {
                "name": "Fiscal year B",
                "company_id": self.company.id,
                "allow_overlap": False,
            }
        )

    def test_default_company(self):
        dr = self.date_range.create(
            {
                "name": "FS2016",
                "date_start": "2015-01-01",
                "date_end": "2016-12-31",
                "type_id": self.type.id,
            }
        )
        self.assertTrue(dr.company_id)
        # you can specify company_id to False
        dr = self.date_range.create(
            {
                "name": "FS2016_NO_COMPANY",
                "date_start": "2015-01-01",
                "date_end": "2016-12-31",
                "type_id": self.type.id,
                "company_id": False,
            }
        )
        self.assertFalse(dr.company_id)

    def test_empty_company(self):
        dr = self.date_range.create(
            {
                "name": "FS2016",
                "date_start": "2015-01-01",
                "date_end": "2016-12-31",
                "type_id": self.type.id,
                "company_id": None,
            }
        )
        self.assertEqual(dr.name, "FS2016")

    def test_invalid(self):
        with self.assertRaises(ValidationError) as cm:
            self.date_range.create(
                {
                    "name": "FS2016",
                    "date_end": "2015-01-01",
                    "date_start": "2016-12-31",
                    "type_id": self.type.id,
                }
            )
        message = str(cm.exception.args[0])
        self.assertEqual(
            message, "FS2016 is not a valid range (2016-12-31 > 2015-01-01)"
        )

    def test_overlap(self):
        self.date_range.create(
            {
                "name": "FS2015",
                "date_start": "2015-01-01",
                "date_end": "2015-12-31",
                "type_id": self.type.id,
            }
        )
        with self.assertRaises(ValidationError) as cm, self.env.cr.savepoint():
            self.date_range.create(
                {
                    "name": "FS2016",
                    "date_start": "2015-01-01",
                    "date_end": "2016-12-31",
                    "type_id": self.type.id,
                }
            )
        message = str(cm.exception.args[0])
        self.assertEqual(message, "FS2016 overlaps FS2015")
        # check it's possible to overlap if it's allowed by the date range type
        self.type.allow_overlap = True
        dr = self.date_range.create(
            {
                "name": "FS2016",
                "date_start": "2015-01-01",
                "date_end": "2016-12-31",
                "type_id": self.type.id,
            }
        )
        self.assertEqual(dr.name, "FS2016")

    def test_domain(self):
        dr = self.date_range.create(
            {
                "name": "FS2015",
                "date_start": "2015-01-01",
                "date_end": "2015-12-31",
                "type_id": self.type.id,
            }
        )
        domain = dr.get_domain("my_field")
        # By default the domain include limits
        self.assertEqual(
            domain,
            [
                ("my_field", ">=", datetime.date(2015, 1, 1)),
                ("my_field", "<=", datetime.date(2015, 12, 31)),
            ],
        )

    def test_date_range_multicompany_1(self):
        with self.assertRaises(UserError):
            self.date_range.create(
                {
                    "name": "FS2016",
                    "date_start": "2015-01-01",
                    "date_end": "2016-12-31",
                    "type_id": self.typeB.id,
                    "company_id": self.company_2.id,
                }
            )
