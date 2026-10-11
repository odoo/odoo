from odoo import Command

from odoo.addons.l10n_es_edi_tbai.tests.common import TestEsEdiTbaiCommonGipuzkoa
from odoo.addons.point_of_sale.tests.common import TestPoSCommon


class TestL10nEsEdiTbaiPosCommon(TestEsEdiTbaiCommonGipuzkoa, TestPoSCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # TestPoSCommon.setUpClass() overwrites the company's country with a neutral
        # placeholder for generic PoS tests; put it back to Spain for this module's tests.
        cls.company_data['company'].country_id = cls.env.ref('base.es').id

        cls.product = cls.env['product.product'].create({
            'name': 'tbai_pos_product',
            'default_code': "product_tbai",
            'lst_price': 100.0,
            'property_account_income_id': cls.company_data['default_account_revenue'].id,
            'property_account_expense_id': cls.company_data['default_account_expense'].id,
            'taxes_id': [Command.set(cls._get_tax_by_xml_id('s_iva21b').ids)],
            'company_id': cls.company_data['company'].id,
            'available_in_pos': True,
        })
