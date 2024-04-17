# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from odoo.tests import tagged

from odoo.addons.sale.tests.common import SaleCommon
from odoo.addons.sale_pdf_quote_builder.const import DEFAULT_FORM_FIELD_PATH_MAPPING


@tagged('-at_install', 'post_install')
class TestPDFQuoteBuilder(SaleCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.path_mapping = json.loads(cls.env['ir.config_parameter'].get_param(
            'sale_pdf_quote_builder.form_field_path_mapping', DEFAULT_FORM_FIELD_PATH_MAPPING
        ))

    def test_dynamic_fields_mapping(self):
        sol_1, sol_2 = self.sale_order.order_line
        fields_to_map = {
            f'sol_id_{sol_1.id}__price_unit',  # float
            f'sol_id_{sol_2.id}__user_id__name',  # char
            f'sol_id_{sol_2.id}__validity_date',  # date
            f'sol_id_{sol_1.id}__delivery_date',  # datetime
            f'sol_id_{sol_1.id}__tax_excl_price',  # datetime

            # TODO
            f'sol_id_{sol_2.id}__user_id',  # relational
            f'sol_id_{sol_2.id}__state',  # selection
            f'sol_id_{sol_1.id}__is_downpayment',  # boolean
            f'sol_id_{sol_2.id}__all_products',  # relational multi
        }
        mapping = self.env['ir.actions.report']._get_form_fields_values_mapping(
            self.sale_order,
            fields_to_map,
            self.path_mapping,
        )
        self.assertEqual(len([val for val in mapping.values() if not val]), 5)  # 4 last + delivery_date

        new_path_mapping = dict(self.path_mapping)
        new_path_mapping['product_document'].update({
            'user_id': 'salesman_id',
            'all_products': 'order_id.order_line.product_id',
            'is_downpayment': 'is_downpayment',
            'state': 'state',
        })
        mapping = self.env['ir.actions.report']._get_form_fields_values_mapping(
            self.sale_order,
            fields_to_map,
            new_path_mapping,
        )
        self.assertEqual(len([val for val in mapping.values() if not val]), 1)  # delivery_date only
