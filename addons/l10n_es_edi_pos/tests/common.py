# Part of Odoo. See LICENSE file for full copyright and licensing details.
from contextlib import contextmanager
from unittest.mock import patch

from odoo import Command

from odoo.addons.point_of_sale.tests.common import TestPoSCommon


class TestL10nEsEdiPosCommon(TestPoSCommon):
    """Base of the tests of l10n_es_edi_pos.

    The module does not depend on any EDI, so the fiscal mode is simulated by patching the hook
    the EDI POS modules extend. The tests default to the 'sii' mode: when the EDI POS modules are
    installed alongside (e.g. on the runbot), it is the only one not acting when an order is paid
    (the SII reports the orders in the F4 session closing entry), so nothing is sent while testing.
    """

    _test_user_groups = None  # FIXME list needed groups

    @classmethod
    @TestPoSCommon.setup_country('es')
    def setUpClass(cls):
        super().setUpClass()
        cls.config = cls.basic_config

        cls.tax21 = cls.env['account.tax'].search([
            ('company_id', '=', cls.company.id),
            ('type_tax_use', '=', 'sale'),
            ('amount', '=', 21.0),
            ('l10n_es_type', '=', 'sujeto'),
        ], limit=1)
        cls.product = cls.env['product.product'].create({
            'name': 'es_edi_pos_product',
            'lst_price': 100.0,
            'property_account_income_id': cls.company_data['default_account_revenue'].id,
            'property_account_expense_id': cls.company_data['default_account_expense'].id,
            'taxes_id': [Command.set(cls.tax21.ids)],
            'company_id': cls.company.id,
            'available_in_pos': True,
        })

    def setUp(self):
        super().setUp()
        # A fiscal mode is needed to enable this module, which does nothing without one. The mode
        # does not tie it to SII: it only stands for "an EDI handles the POS orders". SII is the
        # one interfering the least when the EDI modules are installed (e.g. on runbot): unlike
        # TicketBAI and Veri*Factu, it declares nothing when an order is paid. The tests needing
        # another mode patch it with `_patch_fiscal_mode`.
        self.startPatcher(self._patch_fiscal_mode('sii'))

    # -------------------------------------------------------------------------
    # HELPERS
    # -------------------------------------------------------------------------

    def _patch_fiscal_mode(self, mode):
        """Simulate the fiscal mode of the companies, whatever EDI is installed and configured.

        Patching the final method also overrides the extensions of the installed EDI POS modules.

        :param mode: 'tbai', 'sii', 'verifactu', or False for no EDI
        """
        return patch.object(
            self.env.registry['res.company'],
            '_l10n_es_pos_get_available_fiscal_modes',
            lambda company: {mode} if mode else set(),
        )

    @contextmanager
    def with_pos_session(self):
        session = self.open_new_session(0.0)
        yield session
        cash_pm = self.config._get_cash_payment_method()
        session.close_session_from_ui({cash_pm.id: 0})

    def _create_order(self, pos_order_ui_args=None, **data):
        order_data = self.create_ui_order_data(pos_order_ui_args=pos_order_ui_args or {}, **data)
        results = self.env['pos.order'].sync_from_ui([order_data])
        return self.env['pos.order'].browse(results['pos.order'][0]['id'])

    def _create_sale(self, quantity=1.0, **extra):
        """Create and pay an order of `quantity` products (121 per unit, VAT included)."""
        return self._create_order(
            pos_order_lines_ui_args=[(self.product, quantity)],
            payments=[(self.bank_pm1, 121.0 * quantity)],
            **extra,
        )

    def _create_draft(self, quantity=1.0):
        """Create an order synchronized as a draft, as an open restaurant table."""
        return self._create_order(
            pos_order_ui_args={'state': 'draft'},
            pos_order_lines_ui_args=[(self.product, quantity)],
            payments=[],
        )

    def _create_refund(self, order):
        """Refund `order` and pay the refund, as from the backend ("Return Products")."""
        refund = self.env['pos.order'].browse(order.refund()['res_id'])
        refund.to_invoice = False
        self.make_payment(refund, self  .bank_pm1, refund.amount_total)
        return refund
