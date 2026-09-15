from odoo import Command

from odoo.addons.l10n_es_edi_sii.tests.common import TestEsEdiCommon
from odoo.addons.point_of_sale.tests.common import TestPoSCommon


class TestL10nEsEdiSiiPosCommon(TestEsEdiCommon, TestPoSCommon):

    _test_user_groups = None

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.company.l10n_es_sii_tax_agency = 'aeat'

        cls.tax21 = cls.env['account.tax'].search([
            ('company_id', '=', cls.company.id),
            ('type_tax_use', '=', 'sale'),
            ('amount', '=', 21.0),
            ('l10n_es_type', '=', 'sujeto'),
        ], limit=1)

        cls.product = cls.env['product.product'].create({
            'name': 'sii_pos_product',
            'default_code': 'product_sii',
            'lst_price': 100.0,
            'property_account_income_id': cls.company_data['default_account_revenue'].id,
            'property_account_expense_id': cls.company_data['default_account_expense'].id,
            'taxes_id': [Command.set(cls.tax21.ids)],
            'company_id': cls.company.id,
            'available_in_pos': True,
        })
