from odoo.addons.point_of_sale.tests.common import TestPointOfSaleCommon
from odoo.tests import tagged
from ..models.pos import ORDER_FIELDS, LINE_FIELDS
from json import dumps


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestStringToHash(TestPointOfSaleCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.pricelist = cls.env['product.pricelist'].create({
            'name': 'Test Pricelist',
            'currency_id': cls.company_data['company'].currency_id.id,
        })
        cls.company.country_id = cls.env.company.account_fiscal_country_id.id

    def _compute_string_to_hash_original(self, orders):
        def _getattrstring(obj, field_str):
            field_value = obj[field_str]
            if obj._fields[field_str].type == 'many2one':
                field_value = field_value.id
            if obj._fields[field_str].type in ['many2many', 'one2many']:
                field_value = field_value.sorted().ids
            return str(field_value)

        for order in orders:
            values = {}
            for field in ORDER_FIELDS:
                values[field] = _getattrstring(order, field)

            for line in order.lines:
                for field in LINE_FIELDS:
                    k = 'line_%d_%s' % (line.id, field)
                    values[k] = _getattrstring(line, field)
            # make the json serialization canonical
            #  (https://tools.ietf.org/html/draft-staykov-hu-json-canonical-form-00)
            return dumps(values, sort_keys=True,
                            ensure_ascii=True, indent=None,
                            separators=(',', ':'))

    def _create_and_pay_pos_order(self, line_data_list, payments):
        currency = self.company_data['company'].currency_id
        lines = []
        total_tax = 0.0
        total_amount = 0.0

        for idx, line_data in enumerate(line_data_list):
            product = line_data.get('product', self.product_a)
            qty = line_data['qty']
            price_unit = line_data['price_unit']
            taxes = line_data.get('tax_ids', self.tax_sale_a)

            line_tax = sum((tax.amount / 100) * qty * price_unit for tax in taxes)
            line_total = qty * price_unit + line_tax

            total_tax += line_tax
            total_amount += qty * price_unit

            rounded_total = currency.round(line_total)

            lines.append((0, 0, {
                'name': f"OL/000{idx + 1}",
                'product_id': product.id,
                'price_unit': price_unit,
                'qty': qty,
                'tax_ids': [(6, 0, taxes.ids)],
                'price_subtotal': qty * price_unit,
                'price_subtotal_incl': rounded_total,
            }))

        order = self.env['pos.order'].create({
            'company_id': self.company_data['company'].id,
            'partner_id': self.partner_a.id,
            'session_id': self.pos_config.current_session_id.id,
            'lines': lines,
            'amount_total': currency.round(total_amount + total_tax),
            'amount_tax': currency.round(total_tax),
            'amount_paid': 0,
            'amount_return': 0,
            'pricelist_id': self.pricelist.id
        })

        for payment in payments:
            context_payment = {
                "active_ids": [order.id],
                "active_id": order.id
            }
            pos_make_payment = self.env['pos.make.payment'].with_context(context_payment).create({
                'amount': payment['amount'],
                'payment_method_id': payment['payment_method'].id,
            })
            pos_make_payment.with_context(context_payment).check()
        return order

    def test_string_to_hash(self):
        self.pos_config.open_ui()
        order = self._create_and_pay_pos_order([
            {'qty': 1, 'price_unit': 10000, 'product': self.product_a, 'tax_ids': self.tax_sale_a},
            {'qty': 2, 'price_unit': 5000, 'product': self.product_a, 'tax_ids': self.tax_sale_b},
            {'qty': 3, 'price_unit': 2000, 'tax_ids': self.tax_sale_b | self.tax_sale_b}
        ], [
            {'amount': 10000, 'payment_method': self.bank_payment_method},
            {'amount': 8900, 'payment_method': self.cash_payment_method},
            {'amount': 11000, 'payment_method': self.credit_payment_method}
        ])
        self.pos_config.current_session_id.action_pos_session_closing_control()
        self.assertEqual(order.l10n_fr_string_to_hash, self._compute_string_to_hash_original(order))
