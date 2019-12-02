# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch
from odoo.tests.common import TransactionCase


def just_raise(*args):
    raise Exception("We should not be here.")


class TestResConfig(TransactionCase):

    def setUp(self):
        super(TestResConfig, self).setUp()

        self.user = self.env.ref('base.user_admin')
        self.company = self.env['res.company'].create({'name': 'oobO'})
        self.user.write({'company_ids': [(4, self.company.id)], 'company_id': self.company.id})
        Settings = self.env['res.config.settings'].with_user(self.user.id)
        self.config = Settings.create({})

    def test_multi_company_res_config_group(self):
        # Enable/Disable a group in a multi-company environment
        # 1/ All the users should be added/removed from the group
        # and not only the users of the allowed companies
        # 2/ The changes should be reflected for new users (Default User Template)

        company = self.env['res.company'].create({'name': 'My Last Company'})
        partner = self.env['res.partner'].create({
            'name': 'My User'
        })
        user = self.env['res.users'].create({
            'login': 'My User',
            'company_id': company.id,
            'company_ids': [(4, company.id)],
            'partner_id': partner.id,
        })

        ResConfig = self.env['res.config.settings']
        default_values = ResConfig.default_get(list(ResConfig.fields_get()))

        # Case 1: Enable a group
        default_values.update({'group_multi_currency': True})
        ResConfig.create(default_values).execute()
        self.assertTrue(user in self.env.ref('base.group_multi_currency').sudo().users)

        new_partner = self.env['res.partner'].create({'name': 'New User'})
        new_user = self.env['res.users'].create({
            'login': 'My First New User',
            'company_id': company.id,
            'company_ids': [(4, company.id)],
            'partner_id': new_partner.id,
        })
        self.assertTrue(new_user in self.env.ref('base.group_multi_currency').sudo().users)

        # Case 2: Disable a group
        default_values.update({'group_multi_currency': False})
        ResConfig.create(default_values).execute()
        self.assertTrue(user not in self.env.ref('base.group_multi_currency').sudo().users)

        new_partner = self.env['res.partner'].create({'name': 'New User'})
        new_user = self.env['res.users'].create({
            'login': 'My Second New User',
            'company_id': company.id,
            'company_ids': [(4, company.id)],
            'partner_id': new_partner.id,
        })
        self.assertTrue(new_user not in self.env.ref('base.group_multi_currency').sudo().users)

    def test_no_install(self):
        """Make sure that when saving settings,
           no modules are installed if nothing was set to install.
        """
        # check that no module should be installed in the first place
        config_fields = self.config._get_classified_fields()
        for name, module in config_fields['module']:
            if int(self.config[name]):
                self.assertTrue(module.state != 'uninstalled',
                                "All set modules should already be installed.")
        # if we try to install something, raise; so nothing should be installed
        with patch('odoo.addons.base.models.ir_module.Module._button_immediate_function', new=just_raise):
            self.config.execute()

    def test_install(self):
        """Make sure that the previous test is valid, i.e. when saving settings,
           it starts module install if something was set to install.
        """
        config_fields = self.config._get_classified_fields()
        # set the first uninstalled module to install
        module_to_install = next(filter(lambda m: m[1].state == 'uninstalled', config_fields['module']))
        self.config[module_to_install[0]] = True

        with patch('odoo.addons.base.models.ir_module.Module._button_immediate_function', new=just_raise):
            with self.assertRaisesRegex(Exception, "We should not be here."):
                self.config.execute()
