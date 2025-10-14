# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo.tests import Form
from odoo.addons.base.tests.common import SavepointCaseWithUserDemo


class TestDuplicatePartnerBank(SavepointCaseWithUserDemo):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.company_a = cls.env['res.company'].create({"name": "companyA"})
        cls.user_a = cls.env['res.users'].with_company(cls.company_a).create({"name": "userA", "login": "test@test.com", "group_ids": [(6, 0, [cls.env.ref("base.group_user").id, cls.env.ref("base.group_partner_manager").id])]})
        cls.partner_a = cls.env['res.partner'].with_user(cls.user_a).create({"name": "PartnerA", "company_id": cls.company_a.id})
        cls.partner_bank_a = cls.env['res.partner.bank'].with_user(cls.user_a).create({"acc_number": "12345", "partner_id": cls.partner_a.id})

        cls.company_b = cls.env['res.company'].create({"name": "companyB"})
        cls.user_b = cls.env['res.users'].with_company(cls.company_b).create({"name": "userB", "login": "test1@test.com", "group_ids": [(6, 0, [cls.env.ref("base.group_user").id, cls.env.ref("base.group_partner_manager").id])]})
        cls.partner_b = cls.env['res.partner'].with_user(cls.user_b).create({"name": "PartnerB", "company_id": cls.company_b.id})
        cls.partner_bank_b = cls.env['res.partner.bank'].with_user(cls.user_b).create({"acc_number": "12345", "partner_id": cls.partner_b.id})

    def test_duplicate_acc_number_different_company(self):
        self.assertFalse(self.partner_bank_b.duplicate_bank_partner_ids)

    def test_duplicate_acc_number_no_company(self):
        self.partner_a.company_id = False
        self.partner_bank_a.company_id = False
        self.partner_b.company_id = False
        self.partner_bank_b.company_id = False
        self.assertTrue(self.partner_bank_a.duplicate_bank_partner_ids, self.partner_a)

    def test_duplicate_acc_number_b_company(self):
        self.partner_a.company_id = False
        self.partner_bank_a.company_id = False
        self.assertTrue(self.partner_bank_b.duplicate_bank_partner_ids, self.partner_a)

    def test_remove_bank_account_from_partner(self):
        bank = self.env['res.bank'].create({'name': 'SBI Bank'})
        partner = self.env['res.partner'].create({'name': 'Rich Cat'})
        self.partner_bank_a.write({
            'acc_number': '99999',
            'bank_id': bank.id,
            'partner_id': partner.id,
        })

        self.assertEqual(len(partner.bank_ids), 1)

        with Form(partner) as partner_form:
            partner_form.bank_ids.remove(0)

        self.assertEqual(len(partner.bank_ids), 0)

    def test_duplicate_acc_number_inactive_bank_account(self):
        self.partner_bank_b.active = False
        self.assertFalse(self.partner_bank_a.duplicate_bank_partner_ids)
