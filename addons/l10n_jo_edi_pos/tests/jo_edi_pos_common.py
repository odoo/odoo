from odoo import Command
from odoo.tests import tagged
from odoo.addons.l10n_jo_edi.tests.jo_edi_common import JoEdiCommon
from odoo.addons.point_of_sale.tests.common import TestPoSCommon
from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class JoEdiPosCommon(JoEdiCommon, TestPoSCommon, TestPointOfSaleHttpCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_data['company'].write({
            'country_id': cls.env.ref('base.jo').id,
        })

    def _l10n_jo_create_order(self, order_vals):
        self.main_pos_config.with_user(self.pos_user).open_ui()
        order_vals.update({
            'company_id': self.company.id,
            'session_id': self.main_pos_config.current_session_id.id,
            'partner_id': self.partner_jo.id,
            'date_order': order_vals.get('date_order', '2019-01-01'),
        })
        order_vals.setdefault('amount_tax', 0)
        order_vals.setdefault('amount_paid', 0)
        order_vals.setdefault('amount_total', 0)
        order_vals.setdefault('amount_return', 0)
        order_vals['lines'] = [Command.create({'price_subtotal': 0, 'price_subtotal_incl': 0, **line}) for line in order_vals['lines']]
        order = self.env['pos.order'].create(order_vals)
        order._compute_prices()

        if 'currency_id' in order_vals:
            order.currency_id = order_vals['currency_id']

        return order

    def _l10n_jo_create_order_refund(self, order, refund_vals):
        order = self._l10n_jo_create_order(order) if isinstance(order, dict) else order
        order_refund = order._refund()
        if 'lines' in refund_vals:
            for order_line, line_write_vals in zip(order_refund.lines, refund_vals['lines']):
                order_line.write(line_write_vals)
            del refund_vals['lines']
        order_refund.write(refund_vals)
        return order_refund
