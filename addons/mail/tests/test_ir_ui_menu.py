# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import Mock, patch

from odoo.addons.mail.tests.common import MailCommon, mail_new_test_user
from odoo.tests import tagged, users
from odoo.tests.common import warmup


@tagged('mail_thread')
class TestMenuRootLookupByModel(MailCommon):
    """ Test the determination of the best menu root for a given model.

    When sharing a record through a link, it doesn't contain the menu context
    (menu root). To help the user, we try to restore a root menu related to
    the record when redirecting to the record from the link. That's what is tested
    here. For more details see IrUiMenu._get_best_backend_root_menu_id_for_model.
    """
    @classmethod
    def setUpClass(cls):
        """ Setup data for the tests, especially this menu hierarchy:
        - Contacts
            - Contacts (res.partner)
        - Invoicing
            - Customers
                - Customers (res.partner)
            - Companies (res.company)
        - Sales
            - Orders
                - Customers (res.partner)
        - Settings
            - Users & Companies
                - Companies (res.company)
        """
        super().setUpClass()
        Menu = cls.env['ir.ui.menu']
        Action = cls.env['ir.actions.act_window']

        def _new_menu(name, parent_id=None, action=None):
            menu = Menu.create({'name': name, 'parent_id': parent_id})
            if action:
                menu.action = action
            return menu

        new_menu = Mock(side_effect=_new_menu)

        def new_action(name, res_model, path=None, view_mode=None, domain=None, context=None):
            return Action.create({
                'name': name,
                'res_model': res_model,
                'path': path,
                'view_mode': view_mode,
                'domain': domain,
                'context': str(context) if context else {},
                'type': 'ir.actions.act_window',
            })

        # Remove all menus and setup test menu with known results
        Menu.search([]).unlink()

        menu_root_contact = new_menu('Contacts')
        new_menu('Contacts', parent_id=menu_root_contact.id,
                 action=new_action(
                     'Contacts', res_model='res.partner',
                     path='all-contacts',
                     view_mode='kanban,list,form,activity',
                     context={'default_is_company': True},
                     domain='[]'))
        menu_root_invoicing = new_menu('Invoicing')
        new_menu('Companies', parent_id=menu_root_invoicing.id,
                 action=new_action(
                     'Companies', res_model='res.company',
                     view_mode='list,kanban,form'))
        menu_invoicing_customer = new_menu('Customers', parent_id=menu_root_invoicing.id)
        new_menu('Customers', parent_id=menu_invoicing_customer.id,
                 action=new_action(
                     'Customers', res_model='res.partner',
                     path='all-customers',
                     view_mode='kanban,list,form',
                     context={
                         'search_default_customer': 1,
                         'res_partner_search_mode': 'customer',
                         'default_is_company': True,
                         'default_customer_rank': 1,
                     }))
        menu_root_sales = new_menu('Sales')
        menu_sales_orders = new_menu('Orders', parent_id=menu_root_sales.id)
        new_menu('Customers', parent_id=menu_sales_orders.id,
                 action=new_action(
                     'Customers', res_model='res.partner',
                     view_mode='kanban,list,form',
                     context={
                         'search_default_customer': 1,
                         'res_partner_search_mode': 'customer',
                         'default_is_company': True,
                         'default_customer_rank': 1,
                     }))
        menu_root_settings = new_menu('Settings')
        menu_settings_user_and_companies = new_menu(
            'Users & Companies', parent_id=menu_root_settings.id)
        new_menu('Companies', parent_id=menu_settings_user_and_companies.id,
                 action=new_action(
                     'Companies', res_model='res.company',
                     path='all-companies',
                     view_mode='list,kanban,form'))

        cls.menu_count = new_menu.call_count
        cls.menu_root_contact = menu_root_contact
        cls.menu_root_sales = menu_root_sales
        cls.menu_root_settings = menu_root_settings

        cls.user_public = mail_new_test_user(
            cls.env, login='user_public', groups='base.group_public', name='Bert Tartignole')
        cls.user_portal = mail_new_test_user(
            cls.env, login='user_portal', groups='base.group_portal', name='Chell Gladys')

    def patch_get_backend_root_menu_ids(self, model, return_values):
        return patch.object(model.__class__, '_get_backend_root_menu_ids', return_value=return_values)

    def test_initial_data(self):
        self.assertEqual(len(self.env['ir.ui.menu']._visible_menu_ids()), self.menu_count)

    @warmup
    @users('employee')
    def test_look_for_existing_menu_root_user_with_access(self):
        Menu = self.env['ir.ui.menu']
        with (self.patch_get_backend_root_menu_ids(self.env['res.company'], []),
              self.assertQueryCount(employee=2)):
            # Auto-detection: the menu root with a sub-menu having an action with a path is selected
            self.assertEqual(Menu._get_best_backend_root_menu_id_for_model('res.company'),
                             self.menu_root_settings.id)
        # Second time cache is used, so we got 2 queries less
        for idx, (return_values, expected_menu_root_id) in enumerate((
                # Auto-detection
                ([], self.menu_root_contact.id),
                # Menu root defined by the model (and inheritance of), take the first one i.e. the least specific
                ([self.menu_root_sales.id], self.menu_root_sales.id),
                ([self.menu_root_sales.id, self.menu_root_contact.id], self.menu_root_sales.id),
                ([self.menu_root_contact.id, self.menu_root_sales.id], self.menu_root_contact.id),
        )):
            with (self.patch_get_backend_root_menu_ids(self.env['res.partner'], return_values),
                  self.assertQueryCount(employee=0)):
                self.assertEqual(Menu._get_best_backend_root_menu_id_for_model('res.partner'), expected_menu_root_id)

    @warmup
    @users('user_portal', 'user_public')
    def test_look_for_existing_menu_root_user_no_access(self):
        Menu = self.env['ir.ui.menu']
        with self.assertQueryCount(user_portal=2, user_public=2):
            self.assertEqual(Menu._get_best_backend_root_menu_id_for_model('res.partner'), None)
        with self.assertQueryCount(user_portal=1, user_public=1):
            self.assertEqual(Menu._get_best_backend_root_menu_id_for_model('res.company'), None)
        with (self.patch_get_backend_root_menu_ids(
                self.env['res.partner'], [self.menu_root_sales.id, self.menu_root_contact.id]),
              self.assertQueryCount(user_portal=1, user_public=1)):
            self.assertEqual(Menu._get_best_backend_root_menu_id_for_model('res.partner'), None)

    @warmup
    def test_look_for_non_existing_menu_root(self):
        with (self.patch_get_backend_root_menu_ids(self.env['res.bank'], []),
              self.assertQueryCount(__system__=2)):
            self.assertEqual(self.env['ir.ui.menu']._get_best_backend_root_menu_id_for_model('res.bank'), None)
