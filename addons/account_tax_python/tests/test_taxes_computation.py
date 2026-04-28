from odoo.addons.account_tax_python.tests.common import TestTaxCommonAccountTaxPython
from odoo.tests import tagged
from odoo.exceptions import ValidationError

from odoo.addons.account_tax_python.tools.formula_utils import check_formula, normalize_formula


@tagged('post_install', '-at_install')
class TestTaxesComputationTaxFormula(TestTaxCommonAccountTaxPython):

    _test_user_groups = None  # FIXME list needed groups

    def test_formula(self):
        tax = self.python_tax("max(quantity * price_unit * 0.21, quantity * 4.17)")
        document = self.populate_document(self.init_document(lines=[{'price_unit': 130.0, 'tax_ids': tax}]))
        self.assert_base_lines_tax_details(
            document=document,
            expected_base_lines_tax_details=[{
                'total_excluded_currency': 130.0,
                'delta_total_excluded_currency': 0.0,
                'taxes_data': [
                    {
                        'tax_id': tax.id,
                        'base_amount_currency': 130.0,
                        'tax_amount_currency': 27.3,
                    },
                ],
            }],
            expected_base_amount=130.0,
            expected_tax_amount=27.3,
            expected_total_amount=157.3,
        )

        tax = self.python_tax("max(quantity * price_unit * 0.21, quantity * 4.17)", price_include_override='tax_included')
        document = self.populate_document(self.init_document(lines=[{'price_unit': 130.0, 'tax_ids': tax}]))
        self.assert_base_lines_tax_details(
            document=document,
            expected_base_lines_tax_details=[{
                'total_excluded_currency': 102.7,
                'delta_total_excluded_currency': 0.0,
                'taxes_data': [
                    {
                        'tax_id': tax.id,
                        'base_amount_currency': 102.7,
                        'tax_amount_currency': 27.3,
                    },
                ],
            }],
            expected_base_amount=102.7,
            expected_tax_amount=27.3,
            expected_total_amount=130.0,
        )

        tax = self.python_tax("product.volume * quantity * 0.35")
        product = self._create_product(volume=100.0)
        document = self.populate_document(self.init_document(
            lines=[{'price_unit': 100.0, 'product_id': product, 'tax_ids': tax}],
        ))
        self.assert_base_lines_tax_details(
            document=document,
            expected_base_lines_tax_details=[{
                'total_excluded_currency': 100.0,
                'delta_total_excluded_currency': 0.0,
                'taxes_data': [
                    {
                        'tax_id': tax.id,
                        'base_amount_currency': 100.0,
                        'tax_amount_currency': 35.0,
                    },
                ],
            }],
            expected_base_amount=100.0,
            expected_tax_amount=35.0,
            expected_total_amount=135.0,
        )

        tax = self.python_tax('product["volume"] > 100 and 10 or 5')
        product = self._create_product(volume=105.0)
        document = self.populate_document(self.init_document(
            lines=[{'price_unit': 100.0, 'product_id': product, 'tax_ids': tax}],
        ))
        self.assert_base_lines_tax_details(
            document=document,
            expected_base_lines_tax_details=[{
                'total_excluded_currency': 100.0,
                'delta_total_excluded_currency': 0.0,
                'taxes_data': [
                    {
                        'tax_id': tax.id,
                        'base_amount_currency': 100.0,
                        'tax_amount_currency': 10.0,
                    },
                ],
            }],
            expected_base_amount=100.0,
            expected_tax_amount=10.0,
            expected_total_amount=110.0,
        )

        tax = self.python_tax('product["volume"] > 100 and 10 or 5')
        product = self._create_product(volume=50.0)
        document = self.populate_document(self.init_document(
            lines=[{'price_unit': 100.0, 'product_id': product, 'tax_ids': tax}],
        ))
        self.assert_base_lines_tax_details(
            document=document,
            expected_base_lines_tax_details=[{
                'total_excluded_currency': 100.0,
                'delta_total_excluded_currency': 0.0,
                'taxes_data': [
                    {
                        'tax_id': tax.id,
                        'base_amount_currency': 100.0,
                        'tax_amount_currency': 5.0,
                    },
                ],
            }],
            expected_base_amount=100.0,
            expected_tax_amount=5.0,
            expected_total_amount=105.0,
        )

        tax = self.python_tax('product.volume > 100 and 5 or None')
        product = self._create_product(volume=50.0)
        document = self.populate_document(self.init_document(
            lines=[{'price_unit': 100.0, 'product_id': product, 'tax_ids': tax}],
        ))
        self.assert_base_lines_tax_details(
            document=document,
            expected_base_lines_tax_details=[{
                'total_excluded_currency': 100.0,
                'delta_total_excluded_currency': 0.0,
                'taxes_data': [],
            }],
            expected_base_amount=100.0,
            expected_tax_amount=0.0,
            expected_total_amount=100.0,
        )

        tax = self.python_tax('(product.volume or 5.0) and 0.0 or 10.0')
        product = self._create_product(volume=0.0)
        document = self.populate_document(self.init_document(
            lines=[{'price_unit': 100.0, 'product_id': product, 'tax_ids': tax}],
        ))
        self.assert_base_lines_tax_details(
            document=document,
            expected_base_lines_tax_details=[{
                'total_excluded_currency': 100.0,
                'delta_total_excluded_currency': 0.0,
                'taxes_data': [
                    {
                        'tax_id': tax.id,
                        'base_amount_currency': 100.0,
                        'tax_amount_currency': 10.0,
                    },
                ],
            }],
            expected_base_amount=100.0,
            expected_tax_amount=10.0,
            expected_total_amount=110.0,
        )

        tax = self.python_tax('max(product.volume, 5.0) + 0.0 + -.0')
        product = self._create_product(volume=0.0)
        document = self.populate_document(self.init_document(
            lines=[{'price_unit': 100.0, 'product_id': product, 'tax_ids': tax}],
        ))
        self.assert_base_lines_tax_details(
            document=document,
            expected_base_lines_tax_details=[{
                'total_excluded_currency': 100.0,
                'delta_total_excluded_currency': 0.0,
                'taxes_data': [
                    {
                        'tax_id': tax.id,
                        'base_amount_currency': 100.0,
                        'tax_amount_currency': 5.0,
                    },
                ],
            }],
            expected_base_amount=100.0,
            expected_tax_amount=5.0,
            expected_total_amount=105.0,
        )

        tax = self.python_tax('(max(product.volume, 5.0) + base * 0.05) and None')
        product = self._create_product(volume=0.0)
        document = self.populate_document(self.init_document(
            lines=[{'price_unit': 100.0, 'product_id': product, 'tax_ids': tax}],
        ))
        self.assert_base_lines_tax_details(
            document=document,
            expected_base_lines_tax_details=[{
                'total_excluded_currency': 100.0,
                'delta_total_excluded_currency': 0.0,
                'taxes_data': [],
            }],
            expected_base_amount=100.0,
            expected_tax_amount=0.0,
            expected_total_amount=100.0,
        )

        tax = self.python_tax("min(max(price_unit, quantity), base) * 0.10 + (5 < product['volume'] < 10 and 1.0 or 0.0)")
        product = self._create_product(volume=7.0)
        document = self.populate_document(self.init_document(
            lines=[{'price_unit': 20.0, 'product_id': product, 'tax_ids': tax}],
        ))
        self.assert_base_lines_tax_details(
            document=document,
            expected_base_lines_tax_details=[{
                'total_excluded_currency': 20.0,
                'delta_total_excluded_currency': 0.0,
                'taxes_data': [
                    {
                        'tax_id': tax.id,
                        'base_amount_currency': 20.0,
                        'tax_amount_currency': 3.0,
                    },
                ],
            }],
            expected_base_amount=20.0,
            expected_tax_amount=3.0,
            expected_total_amount=23.0,
        )

        tax = self.python_tax("uom.relative_factor")
        uom = self._create_uom('test_tax_formula', relative_factor=42.0)
        document = self.populate_document(self.init_document(
            lines=[{'price_unit': 100.0, 'product_uom_id': uom, 'tax_ids': tax}],
        ))
        self.assert_base_lines_tax_details(
            document=document,
            expected_base_lines_tax_details=[{
                'total_excluded_currency': 100.0,
                'delta_total_excluded_currency': 0.0,
                'taxes_data': [
                    {
                        'tax_id': tax.id,
                        'base_amount_currency': 100.0,
                        'tax_amount_currency': 42.0,
                    },
                ],
            }],
            expected_base_amount=100.0,
            expected_tax_amount=42.0,
            expected_total_amount=142.0,
        )

        self._run_js_tests()

    def test_invalid_formula(self):
        invalid_formulas = [
            'product.product_tmpl_id',  # no relational fields
            'product.sudo()',  # You don't have access to any record.
            'tuple(1, 2, 3)',  # only min/max functions, no other callables
            'set(1, 2, 3)',
            '[1, 2, 3]',
            '1,',
            '{1, 2}',
            '{1: 2}',
            '(i for _ in product)',
            '"test"',  # strings are only allowed in subscripts of product
            'product[min("volume", "price")]',
            'product()',
            'product[0]',
            'product[:10]',
            'product["field_that_does_not_exist"]',
            'product.field_that_does_not_exist',
            'product.ids',
            'product._fields',
            'product.env.cr',
            'range(1, 10)',
        ]

        for formula in invalid_formulas:
            with self.subTest(formula=formula):
                with self.assertRaises(ValidationError):
                    self.python_tax(formula=formula)

    def test_ast_transformer_normalizes(self):
        # this test simply checks that the AST transformer does not raise any error when
        # collecting attributes and rewriting the formula, and also to list a couple of edge cases.
        # of course all these weird edge cases must be filtered out by the validator later on
        valid_cases = [
            (
                "((10_000 / product.__dunders__) * (product['shall'] - product[\"n0t\"] + ((product._pass)))) -.01",
                "10000 / product['__dunders__'] * (product['shall'] - product['n0t'] + product['_pass']) - 0.01",
                {"__dunders__", "shall", "n0t", "_pass"}
            ),
            (
                "-bob[eats(product . sandwich)] + +product. \\\nwith_fries_inside and product['IS_THE_WAY']",
                "-bob[eats(product['sandwich'])] + +product['with_fries_inside'] and product['IS_THE_WAY']",
                {"sandwich", "with_fries_inside", "IS_THE_WAY"}
            ),
            (
                "(product.help_youself, product['with some']) if product[None] else product.tarte_al_djote['grault']",
                "(product['help_youself'], product['with some']) if product[None] else product['tarte_al_djote']['grault']",
                {"help_youself", "with some", "tarte_al_djote"}
            ),
        ]

        for formula, expected_normalized, expected_fields in valid_cases:
            with self.subTest(code=formula):
                normalized_formula, accessed_fields = normalize_formula(self.env, formula)
                self.assertEqual(accessed_fields['product.product'], expected_fields)
                self.assertEqual(normalized_formula, expected_normalized)

    def test_ast_validator(self):
        to_fail = [
            # no attributes
            # transformer pass before validation rewrote attrs to subscripts,
            # so we don't allow attributes in validation step
            "product.field",
            "isinstance",
            "product.env",
            "(None for _ in ()).gi_frame.f_builtins['__import__']",

            # only whitelisted nodes (no tuples, sets, dicts, lists, etc)
            "1,",
            "product,",
            "min(1, 2),",
            "()",
            "{}",
            "[]",
            "{1: product}",
            "{1, 2}",
            "[product]",
            "(None for _ in product)",

            # only string subscripts of product are allowed
            "product[None]",
            "product[1]",
            "product[:]",
            "not_product['field']",

            # no arbitrary function calls
            "product['a_callable']()",
            "product()",
            "(min or max)(1, 2)",
            "isinstance(1, ())",

            # no arbitrary name load
            "a",
            "__builtins__",
            "isinstance",
        ]
        for formula in to_fail:
            with self.subTest(code=formula):
                with self.assertRaises(ValidationError):
                    check_formula(self.env, formula)
