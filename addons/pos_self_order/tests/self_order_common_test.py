# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import uuid

import odoo.tests

from odoo import Command
from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.addons.point_of_sale.tests.common import archive_products


@odoo.tests.tagged("post_install", "-at_install")
class SelfOrderCommonTest(odoo.tests.HttpCase):
    browser_size = "375x667"
    touch_enabled = True
    allow_inherited_tests_method = True

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        archive_products(cls.env)
        cls.pos_user = mail_new_test_user(
            cls.env,
            groups="base.group_user,point_of_sale.group_pos_user",
            login="pos_user",
            name="POS User",
            tz="Europe/Brussels",
        )
        cls.pos_admin = mail_new_test_user(
            cls.env,
            groups="base.group_user,point_of_sale.group_pos_manager",
            login="pos_admin",
            name="POS Admin",
            tz="Europe/Brussels",
        )

        pos_categ_misc = cls.env['pos.category'].create({
            'name': 'Miscellaneous',
        })

        cls.cola = cls.env['product.product'].create({
            'name': 'Coca-Cola',
            'is_storable': True,
            'list_price': 2.2,
            'taxes_id': False,
            'available_in_pos': True,
            'pos_categ_ids': [(4, pos_categ_misc.id)],
            'default_code': '12345',
        })
        cls.free = cls.env['product.product'].create({
            'name': 'Free',
            'is_storable': True,
            'list_price': 0,
            'taxes_id': False,
            'available_in_pos': True,
            'pos_categ_ids': [(4, pos_categ_misc.id)],
            'default_code': '12345',
        })
        cls.fanta = cls.env['product.product'].create({
            'name': 'Fanta',
            'is_storable': True,
            'list_price': 2.2,
            'taxes_id': False,
            'available_in_pos': True,
            'pos_categ_ids': [(4, pos_categ_misc.id)],
        })
        cls.ketchup = cls.env['product.product'].create({
            'name': 'Ketchup',
            'is_storable': True,
            'list_price': 0,
            'taxes_id': False,
            'available_in_pos': True,
            'pos_categ_ids': [(4, pos_categ_misc.id)],
        })

        #desk organizer
        cls.desk_organizer = cls.env['product.product'].create({
            'name': 'Desk Organizer',
            'available_in_pos': True,
            'list_price': 5.10,
            'pos_categ_ids': [(4, pos_categ_misc.id)],
        })
        desk_size_attribute = cls.env['product.attribute'].create({
            'name': 'Size',
            'display_type': 'radio',
            'create_variant': 'no_variant',
        })
        desk_size_s = cls.env['product.attribute.value'].create({
            'name': 'S',
            'attribute_id': desk_size_attribute.id,
        })
        desk_size_m = cls.env['product.attribute.value'].create({
            'name': 'M',
            'attribute_id': desk_size_attribute.id,
        })
        desk_size_l = cls.env['product.attribute.value'].create({
            'name': 'L',
            'attribute_id': desk_size_attribute.id,
        })
        cls.env['product.template.attribute.line'].create({
            'product_tmpl_id': cls.desk_organizer.product_tmpl_id.id,
            'attribute_id': desk_size_attribute.id,
            'value_ids': [(6, 0, [desk_size_s.id, desk_size_m.id, desk_size_l.id])]
        })
        desk_fabrics_attribute = cls.env['product.attribute'].create({
            'name': 'Fabric',
            'display_type': 'select',
            'create_variant': 'no_variant',
        })
        desk_fabrics_leather = cls.env['product.attribute.value'].create({
            'name': 'Leather',
            'attribute_id': desk_fabrics_attribute.id,
        })
        desk_fabrics_other = cls.env['product.attribute.value'].create({
            'name': 'Custom',
            'attribute_id': desk_fabrics_attribute.id,
            'is_custom': True,
        })
        cls.env['product.template.attribute.line'].create({
            'product_tmpl_id': cls.desk_organizer.product_tmpl_id.id,
            'attribute_id': desk_fabrics_attribute.id,
            'value_ids': [(6, 0, [desk_fabrics_leather.id, desk_fabrics_other.id])]
        })

    def _add_tax_to_product_from_different_company(self):
        new_company = self.env['res.company'].create({
            'name': 'Test Company',
            'currency_id': self.env.ref('base.USD').id,
            'country_id': self.env.ref('base.us').id,
        })

        self.other_company_tax = (
            self.env["account.tax"]
            .with_company(new_company)
            .create(
                {
                    "name": "Tax that should not be used",
                    "amount": 50,
                    "amount_type": "percent",
                    "tax_group_id": self.env["account.tax.group"]
                    .with_company(new_company)
                    .create(
                        {
                            "name": "Tax Group that should not be used",
                        }
                    )
                    .id,
                    "company_id": new_company.id,
                }
            )
        )

        self.env['product.product'].search([]).with_company(new_company).write({
            'taxes_id': [Command.link(id) for id in self.other_company_tax.ids],
        })

    def setUp(self):
        super().setUp()
        journal_obj = self.env['account.journal']
        main_company = self.env.company
        self.bank_journal = journal_obj.create({
            'name': 'Bank Test',
            'type': 'bank',
            'company_id': main_company.id,
            'code': 'BNK',
            'sequence': 10,
        })

        self.bank_payment_method = self.env['pos.payment.method'].create({
            'name': 'Bank',
            'type': 'bank',
            'journal_id': self.bank_journal.id,
            'outstanding_account_id': self.env['account.chart.template'].with_context(
                allowed_company_ids=self.env.company.root_id.ids,
            ).ref('account_journal_payment_debit_account_id', raise_if_not_found=False).id,
        })

        self.delivery_preset = self.env['pos.preset'].create({
            'name': 'Test-Delivery',
            'service_at': 'delivery',
            'identification': 'address',
            'available_in_self': True,
        })

        self.out_preset = self.env['pos.preset'].create({
            'name': 'Test-Takeout',
            'service_at': 'counter',
            'identification': 'name',
            'available_in_self': True,
        })

        self.in_preset = self.env['pos.preset'].create({
            'name': 'Test-In',
            'service_at': 'table',
            'identification': 'none',
            'available_in_self': True,
        })

        self.pos_config = self.env["pos.config"].create(
            {
                "name": "BarTest",
                "self_ordering_default_user_id": self.pos_user.id,
                "module_pos_restaurant": True,
                "self_ordering_mode": "consultation",
                "floor_ids": self.env["restaurant.floor"].search([]),
                "payment_method_ids": [(4, self.bank_payment_method.id)],
                "use_presets": True,
                "available_preset_ids": [(4, self.out_preset.id), (4, self.in_preset.id), (4, self.delivery_preset.id)],
                "default_preset_id": self.in_preset.id,
            }
        )

        self.default_tax15 = self.env["account.tax"].create(
            {
                "name": "Default Tax for Self Order",
                "amount": 15,
                "amount_type": "percent",
            }
        )

        # We need a table and a floor to be able to do some tours when we do not have demo data.
        # and thus no floors.
        self.pos_main_floor = self.env['restaurant.floor'].create({
            'name': 'Main Floor Test',
            'pos_config_ids': [(4, self.pos_config.id)],
        })

        self.pos_table_1 = self.env['restaurant.table'].create({
            'table_number': 1,
            'floor_id': self.pos_main_floor.id,
            'seats': 4,
            'floor_plan_layout': {'top': 100, 'left': 150, 'width': 100, 'height': 100, 'color': 'green'},
        })

        # we need a default tax fixed at 15% to all product because in the test prices are based on this tax.
        # some time with the localization this may not be the case. So we force it.
        self.env["product.product"].search([]).taxes_id = self.default_tax15

        # A new tax is added to each product and this tax is from a different company.
        # This is important in the test because the added tax should not be used in the tour.
        self._add_tax_to_product_from_different_company()

        self.paired_device = self.env["pos_self_order.kiosk.device"].create({
            'config_id': self.pos_config.id,
            'approved_by': self.pos_admin.id,
            'ip_address': "127.0.0.1",
            'user_agent': "demo",
        })

    def _get_pairing_cookie(self):
        return {'name': self.paired_device._format_auth_cookie_name(self.pos_config.id),
                'value': self.paired_device._format_auth_cookie()}

    def start_tour(self, url_path, tour_name, step_delay=None, **kwargs):
        if not kwargs.get('user') and self.pos_config.self_ordering_mode == 'kiosk':
            pairing_cookie = self._get_pairing_cookie()
            cookies = kwargs.setdefault("cookies", {})
            cookies[pairing_cookie['name']] = pairing_cookie['value']
        super().start_tour(url_path, tour_name, step_delay=step_delay, **kwargs)

    def make_request_to_controller(self, url, params):
        cookies = None
        if self.pos_config.self_ordering_mode == 'kiosk':
            pairing_cookie = self._get_pairing_cookie()
            cookies = {pairing_cookie['name']: pairing_cookie['value']}

        response = self.url_open(
            url,
            json.dumps({'jsonrpc': '2.0', 'params': params}),
            method='POST',
            headers={'Content-Type': 'application/json'},
            cookies=cookies
        )
        return response.json().get('result')

    def _create_order_data(self, lines=None, *, product=None, qty=1, price_unit=None,
                           price_subtotal_incl=0, payments=None, preset=None, table=None,
                           device_type=None, **order_values):
        """Build a payload for the self-order process-order endpoint.

        ``lines`` supports products, attributes, and combo children. ``preset`` and
        ``table`` are optional; the configuration defaults are used when omitted.
        The returned payload includes the configuration access token and the order
        data expected by the mobile or kiosk controller.
        """
        if lines is None:
            lines = [{
                'product': product,
                'qty': qty,
                'price_unit': price_unit if price_unit is not None else product.lst_price,
                'price_subtotal_incl': price_subtotal_incl,
            }]

        device_type = device_type or self.pos_config.self_ordering_mode
        if device_type not in ('mobile', 'kiosk'):
            raise ValueError('A mobile or kiosk self-ordering mode is required')

        # A scanned table only authorizes the request; the controller derives the
        # self_ordering_table_id from it and deliberately ignores client table_id.
        if table is None and device_type == 'mobile' and self.pos_config.self_ordering_service_mode == 'table':
            table = self.pos_table_1
        preset = preset if preset is not None else (
            self.pos_config.default_preset_id if self.pos_config.use_presets else False
        )

        order_lines = []
        relation_mapping = {}
        for line in lines:
            product = line['product']
            qty = line.get('qty', 1)
            attribute_value_ids = line.get('attribute_value_ids', [])
            price_extra = line.get('price_extra')
            if price_extra is None:
                price_extra = sum(
                    self.env['product.template.attribute.value']
                    .browse(attribute_value_ids)
                    .filtered(lambda ptav: ptav.attribute_id.create_variant != 'always')
                    .mapped('price_extra')
                )
            parent_uuid = uuid.uuid4().hex
            order_lines.append([Command.CREATE, 0, {
                'uuid': parent_uuid,
                'product_id': product.id,
                'qty': qty,
                'price_unit': line.get('price_unit', product.lst_price),
                'price_extra': price_extra,
                'price_subtotal': line.get('price_subtotal', 0),
                'price_subtotal_incl': line.get('price_subtotal_incl', 0),
                'tax_ids': product.taxes_id._filter_taxes_by_company(self.env.company).ids,
                'attribute_value_ids': attribute_value_ids,
                'combo_id': line.get('combo_id'),
            }])
            for child in line.get('combo_children', []):
                child_uuid = uuid.uuid4().hex
                order_lines.append([Command.CREATE, 0, {
                    'uuid': child_uuid,
                    'product_id': child['product'].id,
                    'qty': child.get('qty', qty),
                    'price_unit': child.get('price_unit', 0),
                    'price_subtotal': 0,
                    'price_subtotal_incl': 0,
                    'combo_item_id': child['combo_item_id'],
                    'attribute_value_ids': child.get('attribute_value_ids', []),
                }])
                relation_mapping[child_uuid] = {'combo_parent_id': parent_uuid}

        order = {
            'id': None,
            'uuid': uuid.uuid4().hex,
            'session_id': self.pos_config.current_session_id.id,
            'state': order_values.pop('state', 'draft'),
            'preset_id': preset.id if preset else False,
            'amount_total': order_values.pop('amount_total', price_subtotal_incl),
            'amount_paid': order_values.pop('amount_paid', 0),
            'amount_tax': order_values.pop('amount_tax', 0),
            'amount_return': order_values.pop('amount_return', 0),
            'lines': order_lines,
            'payment_ids': payments or [],
            **order_values,
        }
        if relation_mapping:
            order['relations_uuid_mapping'] = {'pos.order.line': relation_mapping}
        return {
            'access_token': self.pos_config.access_token,
            'table_identifier': table.identifier if table else None,
            'order': order,
        }

    def process_self_order(self, lines, *, preset=None, table=None, device_type=None, **order_values):
        """Submit an order through the public self-order endpoint and return it."""
        device_type = device_type or self.pos_config.self_ordering_mode
        order_data = self._create_order_data(
            lines,
            preset=preset,
            table=table,
            device_type=device_type,
            **order_values,
        )
        data = self.make_request_to_controller(
            f'/pos-self-order/process-order/{device_type}', order_data,
        )
        return self.env['pos.order'].browse(data['pos.order'][0]['id'])
