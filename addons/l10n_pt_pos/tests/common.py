import itertools

from odoo import Command, fields
from odoo.tests import new_test_user

from odoo.addons.l10n_pt_certification.tests.common import TestL10nPtCommon

# Each order the till sends carries its own uuid.
_uuids = (f'00000000-0000-4000-8000-{n:012d}' for n in itertools.count(1))


class TestL10nPtPosCommon(TestL10nPtCommon):
    """
    Base of the ``l10n_pt_pos`` suite.

    A PT PoS order is always invoiced, and its invoice is the fiscal document handed to the customer,
    so it is issued -- numbered, signed -- as the order is synced (``l10n_pt_issue_automatically``): an
    invoice-receipt (FR) to an identified customer, a simplified invoice (FS) to an anonymous one
    within its limit, a credit note (NC) for a refund. The PoS invoices in its invoice journal, the
    company's sales journal here, whose FT, FR, FS and NC series are the certification suite's.

    ``order_data()`` builds an order as the till sends it, ``sync()`` sends it as the cashier,
    ``sell()`` does both; time is frozen, so an order is dated and synced at the same instant unless
    the test moves the clock in between.
    """

    @classmethod
    def get_default_groups(cls):
        # The class's own user manages the PoS, as it manages accounting.
        return super().get_default_groups() | cls.quick_ref('point_of_sale.group_pos_manager')

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # ==== Users ====
        cls.cashier = new_test_user(
            cls.env,
            login='pt_cashier',
            groups='base.group_user,point_of_sale.group_pos_user',
            company_id=cls.company_pt.id,
            company_ids=[Command.set(cls.company_pt.ids)],
        )

        # ==== Products ====
        cls.pos_category = cls.env['pos.category'].create({'name': 'Loja'})
        cls.product_goods = cls._create_pos_product('Caneca', 'CANECA', 10.0)
        cls.product_pos_service = cls._create_pos_product('Embrulho', 'EMBRULHO', 10.0, type='service')

        # ==== Payment methods ====
        cls.cash_method = cls.env['pos.payment.method'].create({
            'name': 'Numerário',
            'journal_id': cls.company_data['default_journal_cash'].id,
        })
        cls.card_method = cls.env['pos.payment.method'].create({
            'name': 'Cartão',
            'journal_id': cls.company_data['default_journal_bank'].id,
            'l10n_pt_pos_payment_mechanism': 'CC',
        })
        cls.customer_account_method = cls.env['pos.payment.method'].create({
            'name': 'Conta cliente',
            'split_transactions': True,
            'l10n_pt_pos_payment_mechanism': 'OU',
        })

        # ==== Point of Sale ====
        cls.config = cls.env['pos.config'].create({
            'name': 'Loja Lisboa',
            'company_id': cls.company_pt.id,
            'invoice_journal_id': cls.company_data['default_journal_sale'].id,
            'limit_categories': True,
            'iface_available_categ_ids': [Command.set(cls.pos_category.ids)],
            'payment_method_ids': [Command.set((cls.cash_method + cls.card_method + cls.customer_account_method).ids)],
        })
        cls.final_consumer = cls.env.ref('l10n_pt_certification.pt_final_consumer')

    @classmethod
    def _create_pos_product(cls, name, default_code, price, **vals):
        """A product sold in the PoS at ``price`` + 23 %, with the reference and tax a PT PoS requires."""
        return cls.env['product.product'].create({
            'name': name,
            'default_code': default_code,
            'type': 'consu',
            'list_price': price,
            'available_in_pos': True,
            'pos_categ_ids': [Command.set(cls.pos_category.ids)],
            'taxes_id': [Command.set(cls.tax_sale_23.ids)],
            **vals,
        })

    # -------------------------------------------------------------------------
    # Factories
    # -------------------------------------------------------------------------

    @classmethod
    def open_session(cls, config=None, user=None):
        """Open the PoS ``config`` (``cls.config``) as ``user`` (the cashier), as its Open button does."""
        config = (config or cls.config).with_user(user or cls.cashier)
        config.open_ui()
        session = config.current_session_id
        session.set_opening_control(0, None)
        return session.with_env(cls.env)

    def order_data(self, lines=None, partner=None, payments=None, to_invoice=True, session=None, **vals):
        """
        The values of an order paid at the till, as the till sends them to sync, in the session of
        ``self.config``. ``lines`` are ``(product, qty)``, ``(product, qty, discount)`` or dicts of line
        values (``product_id``, ``qty`` …), by default one ``product_goods``; ``payments`` are
        ``(payment method, amount)``, by default the total in cash. ``partner=None`` is a sale without
        customer.
        """
        session = session or self.config.current_session_id
        line_vals_list = []
        for line in lines or [(self.product_goods, 1)]:
            if not isinstance(line, dict):
                product, qty, discount = (*line, 0.0)[:3]
                line = {'product_id': product.id, 'qty': qty, 'discount': discount}
            product = self.env['product.product'].browse(line['product_id'])
            taxes = product.taxes_id
            price_unit = line.get('price_unit', product.lst_price)
            totals = taxes.compute_all(price_unit * (1 - line.get('discount', 0.0) / 100), session.currency_id, line['qty'], product)
            line_vals_list.append({
                'price_unit': price_unit,
                'price_subtotal': totals['total_excluded'],
                'price_subtotal_incl': totals['total_included'],
                'tax_ids': [Command.set(taxes.ids)],
                'discount': 0.0,
                **line,
            })
        amount_total = sum(line['price_subtotal_incl'] for line in line_vals_list)
        amount_untaxed = sum(line['price_subtotal'] for line in line_vals_list)
        payments = payments or [(self.cash_method, amount_total)]
        uuid = next(_uuids)
        return {
            'uuid': uuid,
            'name': f'Order {uuid}',
            'session_id': session.id,
            'date_order': fields.Datetime.to_string(fields.Datetime.now()),
            'partner_id': partner.id if partner else False,
            'pricelist_id': session.config_id.pricelist_id.id,
            'fiscal_position_id': False,
            'user_id': self.cashier.id,
            'lines': [Command.create(line) for line in line_vals_list],
            'payment_ids': [Command.create({
                'amount': amount,
                'name': fields.Datetime.now(),
                'payment_method_id': method.id,
            }) for method, amount in payments],
            'amount_paid': sum(amount for _method, amount in payments),
            'amount_return': 0.0,
            'amount_tax': amount_total - amount_untaxed,
            'amount_total': amount_total,
            'to_invoice': to_invoice,
            'last_order_preparation_change': '{}',
            **vals,
        }

    def sync(self, *orders_data, user=None):
        """Send ``orders_data`` to the server as the till of ``user`` (the cashier) does; the synced orders."""
        result = self.env['pos.order'].with_user(user or self.cashier).sync_from_ui(list(orders_data))
        return self.env['pos.order'].browse([vals['id'] for vals in result['pos.order']]).filtered(
            lambda order: order.uuid in {data['uuid'] for data in orders_data}
        )

    def sell(self, lines=None, partner=None, payments=None, **vals):
        """An order paid at the till and synced, with its invoice: see ``order_data``."""
        return self.sync(self.order_data(lines, partner, payments, **vals))

    def refund(self, order, qty=None, payments=None, **vals):
        """
        Refund ``qty`` (all) of each line of ``order`` at the till, in cash unless ``payments``: the
        synced refund order.
        """
        lines = [{
            'product_id': line.product_id.id,
            'qty': -(line.qty if qty is None else qty),
            'price_unit': line.price_unit,
            'discount': line.discount,
            'refunded_orderline_id': line.id,
        } for line in order.lines]
        return self.sell(lines, order.partner_id, payments, **vals)

    def receipt(self, order, user=None):
        """What the till prints on ``order``'s receipt, read as ``user`` (the cashier)."""
        return order.with_user(user or self.cashier).l10n_pt_get_order_vals()

    def print_receipt(self, order, user=None):
        """Print ``order``'s receipt at the till of ``user`` (the cashier), which counts as a print of its invoice."""
        order.with_user(user or self.cashier).update_l10n_pt_print_version()
