# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo
from odoo.addons.point_of_sale.tests.common import CommonPosTest


@odoo.tests.tagged('post_install', '-at_install')
class TestPointOfSaleSync(CommonPosTest):
    def test_notify_synchronisation_with_archived_employee(self):
        """
        Ensure that synchronizing data containing an archived employee
        does not trigger a backend error.
        """
        self.env.user.group_ids += self.env.ref('hr.group_hr_user')

        emp3 = self.env['hr.employee'].create({
            'name': 'Test Employee 3',
            "company_id": self.env.company.id,
        })
        emp3.write({"active": False})

        self.pos_config_usd.notify_synchronisation(
            session_id=self.pos_config_usd.current_session_id.id,
            device_identifier='1',
            records={
                'pos.session': [],
                'hr.employee': [emp3.id]
            }
        )
