# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged
from odoo.tests.common import ADMIN_USER_ID

from .common import DashboardTestCommon


def no_id(seq):
    """Remove 'id' keys from a list of dicts."""
    for d in seq:
        d.pop('id', None)
    return seq


@tagged("-at_install", "post_install")
class TestDashboardFavoriteFilters(DashboardTestCommon):
    def setUp(self):
        super().setUp()
        self.dashboard = self.create_dashboard()
        self.model = self.env["spreadsheet.dashboard.favorite.filters"]

    def create_filter(self, **vals):
        return self.model.with_user(ADMIN_USER_ID).create(vals)

    def test_own_filters(self):
        self.create_filter(name="A", dashboard_id=self.dashboard.id, user_ids=[self.user.id], global_filters="[]")
        self.create_filter(name="B", dashboard_id=self.dashboard.id, user_ids=[self.user.id], global_filters="[]")
        filters = self.model.with_user(self.user.id).get_filters(self.dashboard.id)
        self.assertEqual(no_id(filters), [
            dict(name="A", is_default=False, user_ids=[self.user.id], global_filters="[]"),
            dict(name="B", is_default=False, user_ids=[self.user.id], global_filters="[]")
        ])

    def test_global_filters(self):
        self.create_filter(name="A", dashboard_id=self.dashboard.id, user_ids=[], global_filters="[]")
        self.create_filter(name="B", dashboard_id=self.dashboard.id, user_ids=[], global_filters="[]")
        filters = self.model.with_user(self.user.id).get_filters(self.dashboard.id)
        self.assertEqual(no_id(filters), [
            dict(name="A", is_default=False, user_ids=[], global_filters="[]"),
            dict(name="B", is_default=False, user_ids=[], global_filters="[]")
        ])

    def test_no_third_party_filters(self):
        self.create_filter(name="A", dashboard_id=self.dashboard.id, user_ids=[], global_filters="[]")
        self.create_filter(name="B", dashboard_id=self.dashboard.id, user_ids=[ADMIN_USER_ID], global_filters="[]")
        self.create_filter(name="C", dashboard_id=self.dashboard.id, user_ids=[self.user.id], global_filters="[]")
        filters = self.model.with_user(self.user.id).get_filters(self.dashboard.id)
        self.assertEqual(no_id(filters), [
            dict(name="A", is_default=False, user_ids=[], global_filters="[]"),
            dict(name="C", is_default=False, user_ids=[self.user.id], global_filters="[]")
        ])

    def test_filters_bound_to_dashboard(self):
        dashboard2 = self.create_dashboard()
        self.create_filter(name="A", dashboard_id=self.dashboard.id, user_ids=[], global_filters="[]")
        self.create_filter(name="B", dashboard_id=dashboard2.id, user_ids=[], global_filters="[]")
        filters = self.model.with_user(self.user.id).get_filters(self.dashboard.id)
        self.assertEqual(no_id(filters), [
            dict(name="A", is_default=False, user_ids=[], global_filters="[]"),
        ])
