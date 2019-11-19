# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import ValidationError
from odoo.tests.common import SavepointCase


class TestIrDefault(SavepointCase):

    @classmethod
    def setUpClass(cls):
        res = super(TestIrDefault, cls).setUpClass()
        cls.companyA = cls.env.company
        cls.companyB = cls.companyA.create({'name': 'CompanyB'})
        cls.user1 = cls.env.user
        cls.user2 = cls.user1.create({'name': 'u2', 'login': 'u2'})
        cls.user3 = cls.user1.create({'name': 'u3', 'login': 'u3',
                              'company_id': cls.companyB.id,
                              'company_ids': cls.companyB.ids})
        return res

    def test_defaults(self):
        """ check the mechanism of user-defined defaults """
        # create some default value for some model
        IrDefault1 = self.env['ir.default'].with_context(allowed_company_ids=[self.companyA.id])
        IrDefault2 = IrDefault1.with_user(self.user2).with_context(allowed_company_ids=[self.companyA.id])
        IrDefault3 = IrDefault1.with_user(self.user3).with_context(allowed_company_ids=[self.companyB.id])

        # set a default value for all users
        IrDefault1.search([('field_id.model', '=', 'res.partner')]).unlink()
        IrDefault1.set('res.partner', 'ref', 'GLOBAL', user_id=False, company_id=False)
        self.assertEqual(IrDefault1.get_model_defaults('res.partner'), {'ref': 'GLOBAL'},
                         "Can't retrieve the created default value for all users.")
        self.assertEqual(IrDefault2.get_model_defaults('res.partner'), {'ref': 'GLOBAL'},
                         "Can't retrieve the created default value for all users.")
        self.assertEqual(IrDefault3.get_model_defaults('res.partner'), {'ref': 'GLOBAL'},
                         "Can't retrieve the created default value for all users.")

        # set a default value for current company (behavior of 'set default' from debug mode)
        IrDefault1.set('res.partner', 'ref', 'COMPANY', user_id=False, company_id=True)
        self.assertEqual(IrDefault1.get_model_defaults('res.partner'), {'ref': 'COMPANY'},
                         "Can't retrieve the created default value for company.")
        self.assertEqual(IrDefault2.get_model_defaults('res.partner'), {'ref': 'COMPANY'},
                         "Can't retrieve the created default value for company.")
        self.assertEqual(IrDefault3.get_model_defaults('res.partner'), {'ref': 'GLOBAL'},
                         "Unexpected default value for company.")

        # set a default value for current user (behavior of 'set default' from debug mode)
        IrDefault2.set('res.partner', 'ref', 'USER', user_id=True, company_id=True)
        self.assertEqual(IrDefault1.get_model_defaults('res.partner'), {'ref': 'COMPANY'},
                         "Can't retrieve the created default value for user.")
        self.assertEqual(IrDefault2.get_model_defaults('res.partner'), {'ref': 'USER'},
                         "Unexpected default value for user.")
        self.assertEqual(IrDefault3.get_model_defaults('res.partner'), {'ref': 'GLOBAL'},
                         "Unexpected default value for company.")

        # check default values on partners
        default1 = IrDefault1.env['res.partner'].default_get(['ref']).get('ref')
        self.assertEqual(default1, 'COMPANY', "Wrong default value.")
        default2 = IrDefault2.env['res.partner'].default_get(['ref']).get('ref')
        self.assertEqual(default2, 'USER', "Wrong default value.")
        default3 = IrDefault3.env['res.partner'].default_get(['ref']).get('ref')
        self.assertEqual(default3, 'GLOBAL', "Wrong default value.")

    def test_conditions(self):
        """ check user-defined defaults with condition """
        IrDefault = self.env['ir.default']

        # default without condition
        IrDefault.search([('field_id.model', '=', 'res.partner')]).unlink()
        IrDefault.set('res.partner', 'ref', 'X')
        self.assertEqual(IrDefault.get_model_defaults('res.partner'),
                         {'ref': 'X'})
        self.assertEqual(IrDefault.get_model_defaults('res.partner', condition='name=Agrolait'),
                         {})

        # default with a condition
        IrDefault.search([('field_id.model', '=', 'res.partner.title')]).unlink()
        IrDefault.set('res.partner.title', 'shortcut', 'X')
        IrDefault.set('res.partner.title', 'shortcut', 'Mr', condition='name=Mister')
        self.assertEqual(IrDefault.get_model_defaults('res.partner.title'),
                         {'shortcut': 'X'})
        self.assertEqual(IrDefault.get_model_defaults('res.partner.title', condition='name=Miss'),
                         {})
        self.assertEqual(IrDefault.get_model_defaults('res.partner.title', condition='name=Mister'),
                         {'shortcut': 'Mr'})

    def test_invalid(self):
        """ check error cases with 'ir.default' """
        IrDefault = self.env['ir.default']
        with self.assertRaises(ValidationError):
            IrDefault.set('unknown_model', 'unknown_field', 42)
        with self.assertRaises(ValidationError):
            IrDefault.set('res.partner', 'unknown_field', 42)
        with self.assertRaises(ValidationError):
            IrDefault.set('res.partner', 'lang', 'some_LANG')
        with self.assertRaises(ValidationError):
            IrDefault.set('res.partner', 'credit_limit', 'foo')

    def test_removal(self):
        """ check defaults for many2one with their value being removed """
        IrDefault = self.env['ir.default']
        IrDefault.search([('field_id.model', '=', 'res.partner')]).unlink()

        # set a record as a default value
        title = self.env['res.partner.title'].create({'name': 'President'})
        IrDefault.set('res.partner', 'title', title.id)
        self.assertEqual(IrDefault.get_model_defaults('res.partner'), {'title': title.id})

        # delete the record, and check the presence of the default value
        title.unlink()
        self.assertEqual(IrDefault.get_model_defaults('res.partner'), {})

    def test_company(self):
        """ check company-dependent defaults """
        # create some defaults in 2 different companies (no bound to a user)
        IrDefault = self.env['ir.default']
        IrDefault.set('res.partner', 'ref', 'foo', company_id=self.companyA.id)
        IrDefault.set('res.partner', 'ref', 'bar', company_id=self.companyB.id)
        # read defaults with 'main allowed company' and check it matches
        defaultA = IrDefault.with_context(allowed_company_ids=[self.companyA.id, self.companyB.id]).get('res.partner', 'ref', company_id=True)
        self.assertEqual(defaultA, 'foo')
        defaultB = IrDefault.with_context(allowed_company_ids=[self.companyB.id, self.companyA.id]).get('res.partner', 'ref', company_id=True)
        self.assertEqual(defaultB, 'bar')
        defaultsA = IrDefault.with_context(allowed_company_ids=[self.companyA.id, self.companyB.id]).get_model_defaults('res.partner')
        self.assertEqual(defaultsA['ref'], 'foo')
        defaultsB = IrDefault.with_context(allowed_company_ids=[self.companyB.id, self.companyA.id]).get_model_defaults('res.partner')
        self.assertEqual(defaultsB['ref'], 'bar')
