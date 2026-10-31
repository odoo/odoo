from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.point_of_sale.tests.common import TestPoSCommon
from odoo.tests import tagged


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestPosKodeTransaksi(TestPoSCommon):
    """ PoS session entries are reported in aggregate, so they get no transaction code """
    _test_user_groups = None  # FIXME list needed groups

    @classmethod
    @AccountTestInvoicingCommon.setup_chart_template('id')
    def setUpClass(cls):
        super().setUpClass()
        cls.config = cls.basic_config
        cls.config.default_partner_id.l10n_id_kode_transaksi = '04'
        cls.customer.l10n_id_kode_transaksi = '04'
        cls.product = cls.create_product('Product', cls.categ_basic, 1000.0, tax_ids=cls.company_data['default_tax_sale'].ids)

    def test_session_move_kode_transaksi(self):
        session = self.open_new_session()
        orders = self._create_orders([
            {'pos_order_lines_ui_args': [(self.product, 1)], 'uuid': 'not_invoiced'},
            {'pos_order_lines_ui_args': [(self.product, 1)], 'customer': self.customer, 'is_invoiced': True, 'uuid': 'invoiced'},
        ])
        cash_pm = session.payment_method_ids.filtered(lambda pm: pm.type == 'cash')[:1]
        session.close_session_from_ui({cash_pm.id: sum(session.order_ids.payment_ids.mapped('amount'))})

        session_move = session.sale_move_ids
        self.assertEqual(session_move.move_type, 'out_invoice')
        self.assertFalse(session_move.l10n_id_kode_transaksi)
        self.assertFalse(session_move.l10n_id_need_kode_transaksi)

        invoice = orders['invoiced'].account_move
        self.assertEqual(invoice.l10n_id_kode_transaksi, '04')
        self.assertTrue(invoice.l10n_id_need_kode_transaksi)
