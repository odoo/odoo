from odoo import Command
from odoo.exceptions import AccessError
from odoo.tests import tagged
from odoo.tools import SQL
from odoo.addons.auth_passkey.tests.test_passkey_demo import PasskeyTest


@tagged('post_install', '-at_install')
class PasskeyTestPortal(PasskeyTest):
    @classmethod
    def setUpClass(self):
        super().setUpClass()
        login = 'passkey_portal'
        self.portal_user = self.env['res.users'].create({
            'name': login,
            'login': login,
            'password': login,
            'group_ids': [Command.set([self.env.ref('base.group_portal').id])],
        })

    def test_passkey_portal_create(self):
        self.env['ir.config_parameter'].sudo().set_param('web.base.url', self.passkeys['test-yubikey']['host'])
        self.admin_user.auth_passkey_key_ids.unlink()
        with self.patch_start_registration(self.passkeys['test-yubikey']['registration']['challenge']):
            self.start_tour("/my/security?debug=tests", 'passkeys_portal_create', login="passkey_portal")

    def test_passkey_portal_rename(self):
        portal_passkey = self.env['auth.passkey.key'].search([('name', '=', 'test-keepassxc')])
        self.env.cr.execute(SQL("UPDATE auth_passkey_key SET create_uid = %s WHERE id = %s", self.portal_user.id, portal_passkey.id))
        self.start_tour("/my/security?debug=tests", 'passkeys_portal_rename', login='passkey_portal')

    def test_passkey_portal_delete(self):
        portal_passkey = self.env['auth.passkey.key'].search([('name', '=', 'test-keepassxc')])
        self.env.cr.execute(SQL("UPDATE auth_passkey_key SET create_uid = %s WHERE id = %s", self.portal_user.id, portal_passkey.id))
        self.start_tour("/my/security?debug=tests", 'passkeys_portal_delete', login='passkey_portal')

    def test_portal_permissions(self):
        admin_passkey = self.env['auth.passkey.key'].search([('name', '=', 'test-yubikey-nano')])
        with self.assertRaises(AccessError):
            admin_passkey.with_user(self.portal_user).write({'name': 'test'})
