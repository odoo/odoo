# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.mail.tests.common import MailCase
from odoo.tests import Form, users
from odoo.tests.common import tagged


@tagged('res_partner_bank')
class TestResPartnerBank(AccountTestInvoicingCommon, MailCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.company_a = cls.env['res.company'].create({"name": "companyA"})
        cls.user_a = cls.env['res.users'].with_company(cls.company_a).create({"name": "userA", "login": "test@test.com", "group_ids": [(6, 0, [cls.env.ref("base.group_user").id, cls.env.ref("base.group_partner_manager").id])]})
        cls.partner_a = cls.env['res.partner'].with_user(cls.user_a).create({"name": "PartnerA", "company_id": cls.company_a.id})
        cls.partner_bank_a = cls.env['res.partner.bank'].with_user(cls.user_a).create({"account_number": "12345", "partner_id": cls.partner_a.id, "company_id": cls.partner_a.company_id.id})

        cls.company_b = cls.env['res.company'].create({"name": "companyB"})
        cls.user_b = cls.env['res.users'].with_company(cls.company_b).create({"name": "userB", "login": "test1@test.com", "group_ids": [(6, 0, [cls.env.ref("base.group_user").id, cls.env.ref("base.group_partner_manager").id])]})
        cls.partner_b = cls.env['res.partner'].with_user(cls.user_b).create({"name": "PartnerB", "company_id": cls.company_b.id})
        cls.partner_bank_b = cls.env['res.partner.bank'].with_user(cls.user_b).create({"account_number": "12345", "partner_id": cls.partner_b.id, "company_id": cls.partner_b.company_id.id})

    @classmethod
    def default_env_context(cls):
        # OVERRIDE to reactivate the tracking
        return {}

    def test_duplicate_acc_number_different_company(self):
        self.assertFalse(self.partner_bank_b.duplicate_bank_partner_ids)

    def test_duplicate_acc_number_no_company(self):
        self.partner_a.company_id = False
        self.partner_bank_a.company_id = False
        self.partner_b.company_id = False
        self.partner_bank_b.company_id = False
        self.env['res.partner.bank'].flush_model()
        self.assertTrue(self.partner_bank_a.duplicate_bank_partner_ids, self.partner_a)

    def test_duplicate_acc_number_b_company(self):
        self.partner_a.company_id = False
        self.partner_bank_a.company_id = False
        self.env['res.partner.bank'].flush_model()
        self.assertTrue(self.partner_bank_b.duplicate_bank_partner_ids, self.partner_a)

    def test_remove_bank_account_from_partner(self):
        # otherwise no unlink rights, unsure what original test was about then :shrug:
        partner = self.env['res.partner'].sudo().create({'name': 'Rich Cat'})
        self.partner_bank_a.write({
            'account_number': '99999',
            'bank_name': 'SBI Bank',
            'partner_id': partner.id,
        })

        self.assertEqual(len(partner.bank_ids), 1)

        with Form(partner) as partner_form:
            partner_form.bank_ids.remove(0)

        self.assertEqual(len(partner.bank_ids), 0)

    def test_duplicate_acc_number_inactive_bank_account(self):
        self.partner_bank_b.active = False
        self.assertFalse(self.partner_bank_a.duplicate_bank_partner_ids)

    def test_tracking(self):
        bank_a = self.partner_bank_a.with_user(self.env.user)
        with self.mock_mail_gateway(), self.mock_mail_app():
            bank_a.write({
                'active': False,
                'allow_out_payment': True,
                'account_number': '99999',
                'clearing_number': '123456789',
                'bank_bic': '9999',
                'holder_name': 'Marcel Offane',
                'partner_id': self.partner_b.id,
            })
            self.flush_tracking()
        self.assertEqual(len(self._new_msgs), 3, 'Should post on old- and new- partners + tracking on bank itself')
        partner_msgs = self._new_msgs.filtered(lambda m: m.model == 'res.partner')
        self.assertEqual(len(partner_msgs), 2)
        self.assertEqual(sorted(partner_msgs.mapped('res_id')), sorted((self.partner_a + self.partner_b).ids))
        for msg in partner_msgs:
            self.assertMessageFields(msg, {
                'body': f'<p>Bank Account <a href="#" data-oe-model="{bank_a._name}" data-oe-id="{bank_a.id}">#{bank_a.id}</a> updated</p>',
                'message_type': 'notification',
                'model': 'res.partner',
                'subtype_id': self.env.ref('mail.mt_note'),
                'tracking_values': [
                    ('active', 'boolean', True, False),
                    ('allow_out_payment', 'boolean', False, True),
                    ('account_number', 'char', '12345', '99999'),
                    ('clearing_number', 'char', False, '123456789'),
                    ('bank_bic', 'char', False, '9999'),
                    ('holder_name', 'char', 'PartnerA', 'Marcel Offane'),
                    ('partner_id', 'many2one', self.partner_a, self.partner_b),
                ],
            })
