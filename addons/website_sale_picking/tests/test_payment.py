from odoo import Command
from odoo.addons.website_sale_picking.tests.common import OnsiteCommon
from odoo.tests import HttpCase, tagged


@tagged('post_install', '-at_install')
class TestOnsitePayment(HttpCase, OnsiteCommon):

    def test_onsite_provider_available_when_onsite_delivery_is_chosen(self):
        order = self._create_so()
        order.carrier_id = self.carrier.id
        compatible_providers = self.env['payment.provider'].sudo()._get_compatible_providers(
            self.company.id, self.partner.id, self.amount, sale_order_id=order.id
        )
        self.assertTrue(any(
            p.code == 'custom' and p.custom_mode == 'onsite' for p in compatible_providers
        ))

    def test_onsite_provider_unavailable_when_no_onsite_delivery(self):
        order = self._create_so()
        compatible_providers = self.env['payment.provider'].sudo()._get_compatible_providers(
            self.company.id, self.partner.id, self.amount, sale_order_id=order.id
        )
        self.assertTrue(not any(
            p.code == 'custom' and p.custom_mode == 'onsite' for p in compatible_providers
        ))

    def test_onsite_payment_fiscal_change_tour(self):
        # Setup fiscal position
        (
            tax_5,
            tax_10,
            tax_15,
        ) = self.env['account.tax'].create([
            {
                'name': '5% Tax',
                'amount_type': 'percent',
                'amount': 5,
                'price_include': False,
                'include_base_amount': False,
                'type_tax_use': 'sale',
            },
            {
                'name': '10% Tax',
                'amount_type': 'percent',
                'amount': 10,
                'price_include': False,
                'include_base_amount': False,
                'type_tax_use': 'sale',
            },
            {
                'name': '15% Tax',
                'amount_type': 'percent',
                'amount': 15,
                'price_include': False,
                'include_base_amount': False,
                'type_tax_use': 'sale',
            },
        ])
        warehouse_fiscal_country = self.env['res.country'].create({
            'name': "Dummy Country",
            'code': 'DC',
        })
        # wsTourUtils.fillAdressForm() selects first country as address country
        client_fiscal_country = self.env['res.country'].search([('code', '=', 'AF')])

        self.env['product.product'].create({
            'name': 'Super Product',
            'list_price': 100.0,
            'type': 'consu',
            'website_published': True,
            'taxes_id': [Command.link(tax_15.id)],
        })

        self.env['account.fiscal.position'].create([
            {
                'name': 'Super Fiscal Position',
                'auto_apply': True,
                'country_id': warehouse_fiscal_country.id,
                'tax_ids': [
                    Command.create({
                        'tax_src_id': tax_15.id,
                        'tax_dest_id': tax_5.id,
                    })
                ],
            },
            {
                'name': 'Super Fiscal Position',
                'auto_apply': True,
                'country_id': client_fiscal_country.id,
                'tax_ids': [
                    Command.create({
                        'tax_src_id': tax_15.id,
                        'tax_dest_id': tax_10.id,
                    }),
                ],
            },
        ])
        self.env.user.company_id.partner_id.country_id = warehouse_fiscal_country
        # Setup onsite picking with fiscal position different than user
        warehouse = self.env['stock.warehouse'].create({
            'name': "Warehouse",
            'partner_id': self.env.user.company_id.partner_id.id,
            'code': "WH01",
        })
        self.carrier.update({
            'warehouse_id': warehouse.id,
        })
        self.start_tour('/shop', 'onsite_payment_fiscal_change_tour')
