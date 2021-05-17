from odoo.addons.phone_validation.tools.phone_validation import phone_format
from odoo.tests.common import Form, SavepointCase


class TestPhone(SavepointCase):

    @classmethod
    def setUpClass(cls):
        super(TestPhone, cls).setUpClass()

        cls.partner_be = cls.env['res.partner'].create({
            'name': 'Partner BE',
            'phone': '+32485001122',
            'mobile': '0032485001122',
        })
        cls.phone_be_formated = '+32 485 00 11 22'

        cls.partner_fr = cls.env['res.partner'].create({
            'name': 'Partner FR',
            'phone': '+33123456789',
            'mobile': '+33 1 23 45 67 89',
        })
        cls.phone_fr_formated = '+33 1 23 45 67 89'
        print(cls.partner_be.fields_get())
        if 'property_account_receivable_id' in cls.partner_be.fields_get():
            user_type_payable = cls.env.ref('account.data_account_type_payable')
            cls.account_payable = cls.env['account.account'].create({
                'code': 'NC1110',
                'name': 'Test Payable Account',
                'user_type_id': user_type_payable.id,
                'reconcile': True
            })
            user_type_receivable = cls.env.ref('account.data_account_type_receivable')
            cls.account_receivable = cls.env['account.account'].create({
                'code': 'NC1111',
                'name': 'Test Receivable Account',
                'user_type_id': user_type_receivable.id,
                'reconcile': True
            })
            cls.partner_be.write({
                'property_account_payable_id': cls.account_payable.id,
                'property_account_receivable_id': cls.account_receivable.id,
            })
            cls.partner_fr.write({
                'property_account_payable_id': cls.account_payable.id,
                'property_account_receivable_id': cls.account_receivable.id,
            })

        cls.lead = cls.env['crm.lead'].create({
            'type': "lead",
            'name': "Test lead new",
            'description': "This is the description of the test new lead.",
        })

    def test_phone_format_partner_lead(self):
        # BE Partner
        partner_phone, partner_mobile = '+32485001122', '0032485001122',
        # check phone_format function result
        partner_phone_formatted = phone_format(partner_phone, 'BE', '32')
        partner_mobile_formatted = phone_format(partner_mobile, 'BE', '32')
        self.assertEqual(partner_phone_formatted, self.phone_be_formated)
        self.assertEqual(partner_mobile_formatted, self.phone_be_formated)
        # ensure initial data
        self.assertEqual(self.partner_be.phone, partner_phone)
        self.assertEqual(self.partner_be.mobile, partner_mobile)
        # change country to trigger onchange who formats phone/mobile
        partner_be_form = Form(self.partner_be)
        partner_be_form.country_id = self.env.ref('base.be')
        partner_be_form.save()
        self.assertEqual(partner_be_form.phone, self.phone_be_formated)
        self.assertEqual(partner_be_form.mobile, self.phone_be_formated)

        # FR Partner
        partner_phone, partner_mobile = '+33123456789', '+33 1 23 45 67 89',
        partner_phone_formatted = phone_format(partner_phone, 'FR', '33')
        partner_mobile_formatted = phone_format(partner_mobile, 'FR', '33')
        self.assertEqual(partner_phone_formatted, self.phone_fr_formated)
        self.assertEqual(partner_mobile_formatted, self.phone_fr_formated)
        self.assertEqual(self.partner_fr.phone, partner_phone)
        self.assertEqual(self.partner_fr.mobile, partner_mobile)
        partner_fr_form = Form(self.partner_fr)
        partner_fr_form.country_id = self.env.ref('base.be')
        partner_fr_form.save()
        self.assertEqual(self.partner_fr.phone, self.phone_fr_formated)
        self.assertEqual(self.partner_fr.mobile, self.phone_fr_formated)

        # Lead
        lead_form = Form(self.lead)
        lead_form.partner_id = self.partner_be # ! updated partner with formated phone
        self.assertEqual(lead_form.phone, self.phone_be_formated,
                         'Lead: form automatically formats numbers')
        self.assertEqual(lead_form.mobile, self.phone_be_formated,
                         'Lead: form automatically formats numbers')

    def test_phone_mobile_search(self):
        for term in ['+33', '0033', '+33123', '0033 123', '+33 123456789', '+33 1 23 45 67 89']:
            self.assertEqual(self.partner_fr, self.env['res.partner'].search([
                ('phone', 'ilike', term), ('name', '=', 'Partner FR'),
            ]))
            self.assertEqual(self.partner_fr, self.env['res.partner'].search([
                ('mobile', 'ilike', term), ('name', '=', 'Partner FR'),
            ]))
