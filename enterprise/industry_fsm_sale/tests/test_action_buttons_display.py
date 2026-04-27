# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import io

from PIL import Image
from datetime import datetime

from odoo.tests import TransactionCase


class TestActionButtons(TransactionCase):
    """ Test visibility of the following buttons:
        - Send/Sign Report
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        if 'worksheet_template_id' in cls.env['project.task']._fields:
            cls.skipTest(cls, '`industry_fsm_report` module must not be installed to run the tests')
        cls.customer = cls.env['res.partner'].create({'name': 'My Customer'})
        cls.env.company.timesheet_encode_uom_id = cls.env.ref('uom.product_uom_hour')
        cls.product_service = cls.env['product.product'].create({
            'name': 'My Service Product',
            'type': 'service',
        })
        cls.product_material = cls.env['product.product'].create({
            'name': 'My Material Product',
            'invoice_policy': 'order',
            'service_type': 'manual',
        })
        cls.project = cls.env['project.project'].create({
            'name': 'My Project',
            'partner_id': cls.customer.id,
            'allow_timesheets': True,
            'allow_material': True,
            'allow_billable': True,
            'timesheet_product_id': cls.product_service.id,
            'is_fsm': True,
            'company_id': cls.env.company.id,
        })
        cls.task = cls.env['project.task'].create({
            'name': 'My Task',
            'project_id': cls.project.id,
            'partner_id': cls.customer.id,
        })
        cls.employee = cls.env['hr.employee'].with_company(cls.env.company).create({
            'name': 'Employee Default',
            'user_id': cls.env.uid,
        })

    def test_send_sign_report_buttons_visibility_conditions(self):
        # Sign/Send not visible if Time = 0 AND Products = 0
        # Visible in non primary if Time > 0 OR Products > 0
        # Visible in primary if Time > 0 AND Products > 0
        # Send should be visible in primary if T,P > 0 and report not sent yet
        # Send should be visible in secondary if T || P > 0 or report already sent

        # Check Enabled Counter
        self.assertEqual(self.task.display_enabled_conditions_count, 2)

        # Sign/send only visible if 'Products on Tasks' is enabled on the project
        self.project.allow_material = False
        self.assertFalse(self.task.display_sign_report_primary)
        self.assertFalse(self.task.display_sign_report_secondary)
        self.assertFalse(self.task.display_send_report_primary)
        self.assertFalse(self.task.display_send_report_secondary)
        self.assertEqual(self.task.display_enabled_conditions_count, 1)

        self.project.allow_timesheets = False
        self.assertEqual(self.task.display_enabled_conditions_count, 0)
        self.project.write({
            'allow_material': True,
            'allow_timesheets': True,
            'timesheet_product_id': self.product_service.id,
        })
        self.assertEqual(self.task.display_enabled_conditions_count, 2)

        # Not visible
        self.assertFalse(self.task.display_sign_report_primary)
        self.assertFalse(self.task.display_sign_report_secondary)
        self.assertFalse(self.task.display_send_report_primary)
        self.assertFalse(self.task.display_send_report_secondary)

        # Secondary if time > 0 only
        self.assertEqual(self.task.display_satisfied_conditions_count, 0)
        timesheet = self.env['account.analytic.line'].create({
            'task_id': self.task.id,
            'project_id': self.project.id,
            'date': datetime.now(),
            'name': 'My Timesheet',
            'user_id': self.env.uid,
            'unit_amount': 1,
        })
        self.assertEqual(self.task.display_satisfied_conditions_count, 1)
        self.assertFalse(self.task.display_sign_report_primary)
        self.assertTrue(self.task.display_sign_report_secondary)
        self.assertFalse(self.task.display_send_report_primary)
        self.assertTrue(self.task.display_send_report_secondary)  # Not signed yet
        timesheet.task_id = False  # Unlink the task from the timesheet

        # Secondary if product > 0 only
        self.assertEqual(self.task.display_satisfied_conditions_count, 0)
        self.task._fsm_ensure_sale_order()
        self.product_material.with_context(fsm_task_id=self.task.id).fsm_add_quantity()
        self.assertEqual(self.task.display_satisfied_conditions_count, 1)
        self.assertTrue(self.task.material_line_product_count)
        self.assertFalse(self.task.display_sign_report_primary)
        self.assertTrue(self.task.display_sign_report_secondary)
        self.assertFalse(self.task.display_send_report_primary)
        self.assertTrue(self.task.display_send_report_secondary)  # Not signed yet

        # Primary of all conditions met
        timesheet.task_id = self.task  # Link the task to the timesheet
        self.assertEqual(self.task.display_satisfied_conditions_count, 2)
        self.assertTrue(self.task.display_sign_report_primary)
        self.assertFalse(self.task.display_sign_report_secondary)
        self.assertTrue(self.task.display_send_report_primary)  # Report is not signed yet
        self.assertFalse(self.task.display_send_report_secondary)  # Report is not signed yet

        # Send visible in primary if report is signed and not sent yet
        f = io.BytesIO()
        Image.new('RGB', (50, 50)).save(f, 'PNG')
        f.seek(0)
        image = base64.b64encode(f.read())
        self.task.worksheet_signature = image
        self.assertTrue(self.task.display_send_report_primary)  # Report is signed, not sent yet
        self.assertFalse(self.task.display_send_report_secondary)
        self.task.fsm_is_sent = True
        self.assertFalse(self.task.display_send_report_primary)
        self.assertFalse(self.task.display_send_report_secondary)  # Report is sent then do not display button
