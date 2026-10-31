from unittest.mock import patch

from odoo.tests import tagged
from odoo.addons.pos_hr.tests.test_frontend import TestPosHrHttpCommon
from odoo.addons.pos_restaurant.tests.test_frontend import TestFrontendCommon


@tagged("post_install", "-at_install")
class TestUi(TestPosHrHttpCommon, TestFrontendCommon):
    def test_post_login_default_screen_tables(self):
        self.main_pos_config.default_screen = "tables"
        self.main_pos_config.with_user(self.pos_admin).open_ui()
        self.start_pos_tour("test_post_login_default_screen_is_tables", login="pos_admin")

    def test_post_login_default_screen_register(self):
        self.main_pos_config.default_screen = "register"
        self.main_pos_config.with_user(self.pos_admin).open_ui()
        self.start_pos_tour("test_post_login_default_screen_is_register", login="pos_admin")

    def test_employee_chatter_with_tracked_order(self):
        """
        Tests that when changing the session's employee mid session,
        the message in the chatter created with the track order setting
        will reflect this change and not keep the old employee
        """
        self.main_pos_config.order_edit_tracking = True
        self.main_pos_config.open_ui()
        self.start_tour(
            "/pos/ui?config_id=%d" % self.main_pos_config.id,
            "test_employee_chatter_with_tracked_order",
            login="pos_admin",
        )
        order = self.env['pos.order'].search([
            ('config_id', '=', self.main_pos_config.id)
        ], order='id desc', limit=1)
        self.assertIn("Test Employee 3", order.message_ids[0].body)


@tagged("post_install", "-at_install")
class TestOrderTrackingWithoutEmployeeLogin(TestFrontendCommon):
    def test_order_tracking_without_employee_login(self):
        other_company = self.env['res.company'].create({'name': 'Other company'})
        # Force an ID collision without depending on the user/employee sequences
        # or changing their values (sequence changes are not rolled back).
        collision_id = max(
            self.env[model].sudo().with_context(active_test=False).search([], order='id desc', limit=1).id
            for model in ('res.users', 'hr.employee')
        ) + 1

        def create_with_collision_id(model, values):
            prepare_create_values = model._prepare_create_values

            def prepare_values(vals_list):
                vals_list = prepare_create_values(vals_list)
                for vals in vals_list:
                    vals['id'] = collision_id
                return vals_list

            with patch.object(type(model), '_prepare_create_values', side_effect=prepare_values):
                return model.create(values)

        employee = create_with_collision_id(self.env['hr.employee'].sudo(), {
            'name': 'Unrelated employee',
            'company_id': other_company.id,
        })
        user = create_with_collision_id(self.env['res.users'], self.pos_user.copy_data({
            'name': 'Order tracking user',
            'login': 'order_tracking_user',
            'password': 'order_tracking_user',
        })[0])
        self.assertEqual(user.id, employee.id)
        self.assertNotIn(other_company, user.company_ids)
        self.assertFalse(self.env['hr.employee.public'].with_user(user).browse(employee.id).has_access('read'))

        self.pos_config.write({'module_pos_hr': False, 'order_edit_tracking': True})
        self.pos_config.with_user(user).open_ui()
        # Order two units, leave the table to sync, reopen it, reduce to one,
        # then pay. The quantity decrease must not read the unrelated employee.
        self.start_pos_tour('OrderTrackingTour', login=user.login)

        order = self.pos_config.current_session_id.order_ids
        self.assertEqual(len(order), 1)
        self.assertEqual(order.state, 'paid')
        self.assertEqual(order.lines.qty, 1)
        self.assertTrue(order.is_edited)
        self.assertIn('Cashier Order tracking user', ''.join(order.message_ids.mapped('body')))
