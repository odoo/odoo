# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import timedelta

from odoo import Command, SUPERUSER_ID, api, fields
from odoo.exceptions import ValidationError
from odoo.tests import tagged, TransactionCase
from odoo.tools import mute_logger


@tagged('post_install', '-at_install', 'event_availability')
class TestEventAvailabilityRace(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        with cls.env.registry.cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})

            product = env['product.product'].create({
                'name': 'Race Ticket',
                'type': 'service',
                'service_tracking': 'event',
                'list_price': 100.0,
                'available_in_pos': True,
                'taxes_id': [],
            })
            cls.product_id = product.id
            cls.product_tmpl_id = product.product_tmpl_id.id

            cls.event_id = env['event.event'].create({
                'name': 'Concurrency Race Event',
                'date_begin': fields.Datetime.now() + timedelta(days=1),
                'date_end': fields.Datetime.now() + timedelta(days=2),
                'seats_limited': True,
                'seats_max': 1,
            }).id

            cls.ticket_id = env['event.event.ticket'].create({
                'name': 'Standard Ticket',
                'event_id': cls.event_id,
                'product_id': cls.product_id,
                'seats_max': 1,
                'price': 100.0,
            }).id

            cls.partner_id = env.ref('base.res_partner_1').id

            payment_method_unknown = env.ref('payment.payment_method_unknown')
            cls.payment_method_id = payment_method_unknown.id
            cls.dummy_provider_id = env['payment.provider'].create({
                'name': 'Dummy Provider',
                'code': 'none',
                'state': 'test',
                'is_published': True,
                'payment_method_ids': [Command.set([payment_method_unknown.id])],
            }).id
            payment_method_unknown.write({'active': True})

            cls.inbound_payment_method_id = env['account.payment.method'].sudo().create({
                'name': 'None (inbound)',
                'payment_type': 'inbound',
                'code': 'none',
            }).id
            provider_journal_id = env['payment.provider'].browse(cls.dummy_provider_id).journal_id.id
            env['account.payment.method.line'].sudo().create({
                'payment_method_id': cls.inbound_payment_method_id,
                'journal_id': provider_journal_id,
            })

            journal_sale = env['account.journal'].search([
                ('type', '=', 'sale'), ('company_id', '=', env.company.id),
            ], limit=1)
            journal_cash = env['account.journal'].search([
                ('type', '=', 'cash'), ('company_id', '=', env.company.id),
            ], limit=1)

            cls.pos_payment_method_id = env['pos.payment.method'].create({
                'name': 'Race Test Cash',
                'journal_id': journal_cash.id,
                'company_id': env.company.id,
            }).id
            pos_config = env['pos.config'].create({
                'name': 'Race Test PoS',
                'journal_id': journal_sale.id,
                'payment_method_ids': [Command.link(cls.pos_payment_method_id)],
            })
            cls.pos_config_id = pos_config.id
            pos_config.open_ui()
            cls.session_id = pos_config.current_session_id.id

            cr.commit()

    @classmethod
    def tearDownClass(cls):
        with cls.env.registry.cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})

            if hasattr(cls, 'session_id'):
                cr.execute("UPDATE pos_session SET state = 'closed' WHERE id = %s", [cls.session_id])
                cr.execute("DELETE FROM pos_payment WHERE pos_order_id IN (SELECT id FROM pos_order WHERE session_id = %s)", [cls.session_id])
                cr.execute("DELETE FROM pos_order_line WHERE order_id IN (SELECT id FROM pos_order WHERE session_id = %s)", [cls.session_id])
                cr.execute("DELETE FROM pos_order WHERE session_id = %s", [cls.session_id])
                cr.execute("DELETE FROM pos_session WHERE id = %s", [cls.session_id])

            if hasattr(cls, 'pos_config_id'):
                cr.execute("DELETE FROM pos_config WHERE id = %s", [cls.pos_config_id])

            if hasattr(cls, 'pos_payment_method_id'):
                cr.execute("DELETE FROM pos_payment_method WHERE id = %s", [cls.pos_payment_method_id])

            cr.execute("DELETE FROM account_payment_method_line WHERE payment_method_id = %s", [cls.inbound_payment_method_id])

            env['account.payment.method'].sudo().search([
                ('code', '=', 'none'),
                ('payment_type', '=', 'inbound')
            ]).unlink()

            provider = env['payment.provider'].browse(cls.dummy_provider_id)
            if provider.exists():
                provider.write({'state': 'disabled'})
                provider.unlink()

            env['event.event.ticket'].browse(cls.ticket_id).unlink()
            env['event.event'].browse(cls.event_id).unlink()
            cr.execute("DELETE FROM product_product WHERE id = %s", [cls.product_id])
            cr.execute("DELETE FROM product_template WHERE id = %s", [cls.product_tmpl_id])

            cr.commit()
        super().tearDownClass()

    def setUp(self):
        super().setUp()
        with self.env.registry.cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            so = env['sale.order'].create({
                'partner_id': self.partner_id,
                'order_line': [Command.create({
                    'product_id': self.product_id,
                    'product_uom_qty': 1,
                    'event_id': self.event_id,
                    'event_ticket_id': self.ticket_id,
                    'price_unit': 100.0,
                    'tax_id': [],
                })],
            })
            self.sale_order_id = so.id
            cr.commit()

        self._aux_envs = [
            api.Environment(self.env.registry.cursor(), SUPERUSER_ID, {}),
            api.Environment(self.env.registry.cursor(), SUPERUSER_ID, {}),
            api.Environment(self.env.registry.cursor(), SUPERUSER_ID, {}),
        ]

    def tearDown(self):
        for env_aux in self._aux_envs:
            env_aux.cr.close()

        with self.env.registry.cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            so = env['sale.order'].browse(self.sale_order_id)
            if so.exists():
                so.transaction_ids.unlink()
                env['event.registration'].search([('event_id', '=', self.event_id)]).unlink()
                so._action_cancel()
                so.unlink()
            cr.commit()
        super().tearDown()

    def _make_pos_order_data(self):
        return {
            "amount_paid": 100,
            "amount_tax": 0,
            "amount_return": 0,
            "amount_total": 100,
            "date_order": fields.Datetime.to_string(fields.Datetime.now()),
            "fiscal_position_id": False,
            "lines": [
                Command.create({
                    "discount": 0,
                    "pack_lot_ids": [],
                    "price_unit": 100.0,
                    "product_id": self.product_id,
                    "price_subtotal": 100.0,
                    "price_subtotal_incl": 100.0,
                    "tax_ids": [],
                    "qty": 1,
                    "event_ticket_id": self.ticket_id,
                    "event_registration_ids": [
                        (0, 0, {
                            "event_id": self.event_id,
                            "event_ticket_id": self.ticket_id,
                            "name": "PoS Racer",
                            "email": "pos@race.com",
                            "phone": "123456789",
                        }),
                    ],
                }),
            ],
            "name": "Order RACE-12345",
            "partner_id": self.partner_id,
            "session_id": self.session_id,
            "sequence_number": 2,
            "payment_ids": [
                Command.create({
                    "amount": 100,
                    "name": fields.Datetime.now(),
                    "payment_method_id": self.pos_payment_method_id,
                }),
            ],
            "uuid": "12345-123-RACE",
            "last_order_preparation_change": "{}",
            "user_id": SUPERUSER_ID,
            "to_invoice": False,
        }

    @mute_logger(
        'odoo.addons.sale.models.payment_transaction',
        'odoo.addons.payment.models.payment_transaction',
    )
    def test_race_website_vs_pos(self):
        env0, env1, env2 = self._aux_envs
        env1.cr.execute('SELECT 1')

        pos_order_data = self._make_pos_order_data()
        env2['pos.order'].sync_from_ui([pos_order_data])
        env2.cr.commit()

        so = env1['sale.order'].browse(self.sale_order_id)
        tx = env1['payment.transaction'].create({
            'amount': so.amount_total,
            'currency_id': so.currency_id.id,
            'provider_id': self.dummy_provider_id,
            'payment_method_id': self.payment_method_id,
            'reference': f'WEB-RACE-{so.name}',
            'operation': 'online_redirect',
            'sale_order_ids': [Command.set([so.id])],
            'partner_id': self.partner_id,
            'state': 'done',
        })

        with self.assertRaises(ValidationError):
            tx._post_process()

        final_count = env0['event.registration'].search_count([('event_id', '=', self.event_id)])
        self.assertEqual(final_count, 1)

    @mute_logger(
        'odoo.addons.sale.models.payment_transaction',
        'odoo.addons.payment.models.payment_transaction',
    )
    def test_race_website_vs_website(self):
        env0, env1, env2 = self._aux_envs
        env2.cr.execute('SELECT 1')

        so1_env1 = env1['sale.order'].browse(self.sale_order_id)
        tx1 = env1['payment.transaction'].with_context(install_mode=True).create({
            'amount': so1_env1.amount_total,
            'currency_id': so1_env1.currency_id.id,
            'provider_id': self.dummy_provider_id,
            'payment_method_id': self.payment_method_id,
            'reference': f'WEB-RACE-1-{so1_env1.name}',
            'operation': 'online_redirect',
            'sale_order_ids': [Command.set([so1_env1.id])],
            'partner_id': self.partner_id,
            'state': 'done',
        })
        tx1._post_process()
        env1.cr.commit()

        so2 = env2['sale.order'].create({
            'partner_id': self.partner_id,
            'order_line': [Command.create({
                'product_id': self.product_id,
                'product_uom_qty': 1,
                'event_id': self.event_id,
                'event_ticket_id': self.ticket_id,
                'price_unit': 100.0,
                'tax_id': [],
            })],
        })

        tx2 = env2['payment.transaction'].with_context(install_mode=True).create({
            'amount': so2.amount_total,
            'currency_id': so2.currency_id.id,
            'provider_id': self.dummy_provider_id,
            'payment_method_id': self.payment_method_id,
            'reference': f'WEB-RACE-2-{so2.name}',
            'operation': 'online_redirect',
            'sale_order_ids': [Command.set([so2.id])],
            'partner_id': self.partner_id,
            'state': 'done',
        })

        try:
            with self.assertRaises(ValidationError):
                tx2._post_process()

            count = env0['event.registration'].search_count([
                ('event_id', '=', self.event_id),
                ('sale_status', '=', 'sold'),
            ])
            self.assertEqual(count, 1)
        finally:
            so2_clean = env0['sale.order'].browse(so2.id)
            if so2_clean.exists():
                so2_clean.transaction_ids.unlink()
                so2_clean._action_cancel()
                so2_clean.unlink()
                env0.cr.commit()
