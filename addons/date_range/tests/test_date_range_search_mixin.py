# Copyright 2016 ACSONE SA/NV (<http://acsone.eu>)
# Copyright 2021 Opener B.V. <stefan@opener.amsterdam>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).
from dateutil.rrule import MONTHLY
from odoo_test_helper import FakeModelLoader

from odoo.tests.common import TransactionCase


class TestDateRangeearchMixin(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Load a test model using odoo_test_helper
        cls.loader = FakeModelLoader(cls.env, cls.__module__)
        cls.loader.backup_registry()
        from .models import TestDateRangeSearchMixin

        cls.loader.update_registry((TestDateRangeSearchMixin,))

        cls.env.user.lang = "en_US"
        rtype = cls.env["date.range.type"].create(
            {"name": __name__, "company_id": False, "allow_overlap": False}
        )
        cls.env["date.range.generator"].create(
            {
                "date_start": "1943-01-01",
                "name_prefix": "1943-",
                "type_id": rtype.id,
                "duration_count": 3,
                "unit_of_time": str(MONTHLY),
                "count": 4,
            }
        ).action_apply()
        cls.ranges = cls.env["date.range"].search([("type_id", "=", rtype.id)])
        cls.model = cls.env[TestDateRangeSearchMixin._name]

    @classmethod
    def tearDownClass(cls):
        cls.loader.restore_registry()
        return super().tearDownClass()

    def test_01_search_view(self):
        """The search field is injected in the model's search view"""
        self.assertIn(
            '<separator/><field name="date_range_search_id" string="Period"/>',
            self.model.get_view(view_type="search")["arch"],
        )
        self.assertNotIn(
            '<separator/><field name="date_range_search_id" string="Period"/>',
            self.model.get_view(view_type="form")["arch"],
        )
        # Having a view with a group element in it
        view = self.env["ir.ui.view"].create(
            {
                "name": __name__,
                "model": self.model._name,
                "arch": """
                <search>
                    <field name="name"/>
                    <group string="Group by">
                        <filter name="name" context="{'group_by': 'name'}"/>
                    </group>
                </search>
            """,
            }
        )
        self.assertIn(
            '<separator/><field name="date_range_search_id" string="Period"/>',
            self.model.get_view(view_type="search")["arch"],
        )
        # Having a view in which the field is added explicitely
        view.arch = """
            <search>
                <field name="name"/>
                <field name="date_range_search_id"/>
                <group string="Group by">
                    <filter name="name" context="{'group_by': 'name'}"/>
                </group>
            </search>
        """
        self.assertNotIn(
            '<separator/><field name="date_range_search_id" string="Period"/>',
            self.model.get_view(view_type="search")["arch"],
        )

    def test_02_search_result(self):
        """Using the search field leads to expected results"""
        record = self.model.create({"test_date": "1943-04-05"})
        self.assertFalse(record.date_range_search_id)
        self.assertIn(
            record,
            self.model.search([("date_range_search_id", "=", self.ranges[1].id)]),
        )
        self.assertNotIn(
            record,
            self.model.search([("date_range_search_id", "!=", self.ranges[1].id)]),
        )
        self.assertIn(
            record,
            self.model.search([("date_range_search_id", "!=", self.ranges[0].id)]),
        )
        self.assertNotIn(
            record,
            self.model.search([("date_range_search_id", "=", self.ranges[0].id)]),
        )
        self.assertIn(
            record, self.model.search([("date_range_search_id", "in", self.ranges.ids)])
        )
        self.assertNotIn(
            record,
            self.model.search([("date_range_search_id", "not in", self.ranges.ids)]),
        )
        self.assertIn(
            record,
            self.model.search([("date_range_search_id", "not in", self.ranges[3].ids)]),
        )
        self.assertNotIn(
            record,
            self.model.search([("date_range_search_id", "in", self.ranges[3].ids)]),
        )
        self.assertIn(
            record, self.model.search([("date_range_search_id", "ilike", "1943")])
        )
        self.assertNotIn(
            record, self.model.search([("date_range_search_id", "not ilike", "1943")])
        )
        self.assertIn(
            record, self.model.search([("date_range_search_id", "not ilike", "2021")])
        )
        self.assertNotIn(
            record, self.model.search([("date_range_search_id", "ilike", "2021")])
        )
        self.assertIn(record, self.model.search([("date_range_search_id", "=", True)]))
        self.assertNotIn(
            record, self.model.search([("date_range_search_id", "=", False)])
        )
        self.assertIn(
            record, self.model.search([("date_range_search_id", "!=", False)])
        )
        self.assertNotIn(
            record, self.model.search([("date_range_search_id", "!=", True)])
        )

    def test_03_read(self):
        """Read returns a falsy value"""
        record = self.model.create({"test_date": "1943-04-05"})
        self.assertFalse(record.date_range_search_id)

    def test_04_load_views(self):
        """Technical field label is replaced in `load_views`"""
        field = self.model.get_views([(None, "form")])["models"][self.model._name][
            "date_range_search_id"
        ]
        self.assertNotIn("technical", field["string"])
