# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import Command
from odoo.addons.account.tests.common import AccountTestInvoicingCommon


class TestMxCommon(AccountTestInvoicingCommon):

    @classmethod
    @AccountTestInvoicingCommon.setup_country('mx')
    def setUpClass(cls):
        super().setUpClass()

        # do not use demo data and avoid having duplicated companies
        cls.env['res.company'].search([('vat', '=', "EKU9003173C9")]).write({'vat': False})
        cls.env['res.company'].search([('name', '=', "ESCUELA KEMPER URGATE")]).name = "ESCUELA KEMPER URGATE (2)"

        cls.company_data['company'].write({
            'name': 'ESCUELA KEMPER URGATE',
            'vat': 'EKU9003173C9',
            'street': 'Campobasso Norte 3206 - 9000',
            'street2': 'Fraccionamiento Montecarlo',
            'zip': '20914',
            'city': 'Jesús María',
            'country_id': cls.env.ref('base.mx').id,
            'state_id': cls.env.ref('base.state_mx_ags').id,
        })

        cls.partner_mx = cls.env['res.partner'].create({
            'name': "INMOBILIARIA CVA",
            'property_account_receivable_id': cls.company_data['default_account_receivable'].id,
            'property_account_payable_id': cls.company_data['default_account_payable'].id,
            'street': "Campobasso Sur 3201 - 9001",
            'city': "Hidalgo del Parral",
            'state_id': cls.env.ref('base.state_mx_chih').id,
            'zip': '33826',
            'country_id': cls.env.ref('base.mx').id,
            'vat': 'ICV060329BY0',
            'bank_ids': [Command.create({'acc_number': "0123456789"})],
        })
