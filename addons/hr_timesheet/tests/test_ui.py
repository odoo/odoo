from odoo.tests import HttpCase


class TestUiCommon(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.bert_user.groups_id += cls.env.ref("hr_timesheet.group_hr_timesheet_user")
        cls.hugo.groups_id += cls.env.ref("hr_timesheet.group_hr_timesheet_user")
