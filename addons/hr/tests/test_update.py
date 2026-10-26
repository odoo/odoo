# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo.tools import SQL

from odoo.addons.base.tests.common import BaseCommon
from odoo.addons.mail.tests.common import mail_new_test_user


class TestUpdateEmployeesCommon(BaseCommon):
    # Executed from a cron no need to test access right
    _test_user_groups = None

    def _count(self):
        return self.env['publisher_warranty.contract']._get_message()['nbr_employees_wo_user']


class TestUpdateEmployeesWithoutUser(TestUpdateEmployeesCommon):

    def test_count_employees(self):
        Employee = self.env['hr.employee']
        before = self._count()
        Employee.create({'name': 'No user'})
        Employee.create({
            'name': 'Portal',
            'user_id': mail_new_test_user(self.env, login='update_portal', groups='base.group_portal').id,
        })
        archived_user = mail_new_test_user(self.env, login='update_archived', groups='base.group_user')
        archived_user.active = False
        Employee.create({'name': 'Archived user', 'user_id': archived_user.id})
        self.assertEqual(self._count(), before)
        Employee.create({
            'name': 'Internal',
            'user_id': mail_new_test_user(self.env, login='update_internal', groups='base.group_user').id,
        })
        employee = Employee.create({'name': 'Archived employee'})
        # Employee without activity shouldn't count
        self.assertEqual(self._count(), before)

        Contract = self.env.registry['publisher_warranty.contract']
        # pretend every employee has some activity in an application
        with patch.object(Contract, '_get_activity_filters', lambda self: [SQL("TRUE")]):
            # Count employee without any user, link to a portal user and link to an archive internal user
            self.assertEqual(self._count(), before + 4)
            # archived employees are never counted
            employee.active = False
            self.env.flush_all()
            self.assertEqual(self._count(), before + 3)
