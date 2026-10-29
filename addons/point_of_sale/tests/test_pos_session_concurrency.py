# Part of Odoo. See LICENSE file for full copyright and licensing details.

from uuid import uuid4

from odoo import SUPERUSER_ID, Command, api
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestPosSessionCloseConcurrency(TransactionCase):
    """ A paid order is synced while another transaction closes its session.
    Both transactions must see the session, so the fixture is committed.
    """

    def setUp(self):
        super().setUp()
        self.uid = self.env.ref('base.user_admin').id
        with self.env.registry.cursor() as cr:
            env = api.Environment(cr, self.uid, {})
            journal = env['account.journal'].search([
                *env['account.journal']._check_company_domain(env.company),
                ('type', '=', 'bank'),
            ], limit=1)
            payment_method = env['pos.payment.method'].create({
                'name': 'Concurrency Bank',
                'type': 'bank',
                'journal_id': journal.id,
            })
            self.config = env['pos.config'].create({
                'name': 'Concurrency Shop',
                'payment_method_ids': [Command.set(payment_method.ids)],
            })
            self.product = env['product.product'].create({
                'name': 'Concurrency Product',
                'available_in_pos': True,
                'taxes_id': [Command.clear()],
            })
            self.config.open_ui()
            self.session = self.config.current_session_id
            self.session.set_opening_control(0, None)
            self.order = {
                'uuid': str(uuid4()),
                'session_id': self.session.id,
                'amount_total': 10.0,
                'amount_tax': 0.0,
                'amount_paid': 10.0,
                'amount_return': 0.0,
                'lines': [Command.create({
                    'product_id': self.product.id,
                    'qty': 1,
                    'price_unit': 10.0,
                    'price_subtotal': 10.0,
                    'price_subtotal_incl': 10.0,
                })],
                'payment_ids': [Command.create({
                    'amount': 10.0,
                    'payment_method_id': payment_method.id,
                })],
            }
        self.addCleanup(self._cleanup)

    def _cleanup(self):
        with self.env.registry.cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            config = env['pos.config'].browse(self.config.id)
            orders = env['pos.order'].search([('config_id', '=', config.id)])
            # write() refuses to cancel a paid order
            orders._write({'state': 'cancel'})
            orders.invalidate_recordset(['state'])
            orders.unlink()
            config.session_ids.unlink()
            payment_methods = config.payment_method_ids
            sequences = config.order_seq_id | config.order_backend_seq_id
            config.unlink()
            payment_methods.unlink()
            sequences.unlink()
            env['product.product'].browse(self.product.id).unlink()

    def _sync_order(self, env):
        env['pos.order'].sync_from_ui([self.order])

    def _close_session(self, env):
        env['pos.session'].browse(self.session.id).close_session_from_ui()

    def _race(self, first, second):
        """ Run `first` and commit it while the transaction of `second` has
        already started, then commit `second`.
        """
        registry = self.env.registry
        with registry.cursor() as first_cr, registry.cursor() as second_cr:
            second_cr.execute('SELECT 1')  # snapshot taken before `first` commits
            first(api.Environment(first_cr, self.uid, {}))
            first_cr.commit()
            second(api.Environment(second_cr, self.uid, {}))
        with registry.cursor() as cr:
            order = api.Environment(cr, self.uid, {})['pos.order'].search([('uuid', '=', self.order['uuid'])])
            if order.session_id.state == 'closed':
                self.assertTrue(
                    order.account_move,
                    f"Order {order.name} is {order.state} in the closed session {order.session_id.name}, "
                    "but the closing of that session did not account it",
                )

    def test_order_committed_during_closing(self):
        self._race(self._sync_order, self._close_session)

    def test_closing_committed_during_order_sync(self):
        self._race(self._close_session, self._sync_order)
