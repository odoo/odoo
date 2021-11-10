odoo.define('l10n_gcc_pos.OrderReceipt', function (require) {
    'use strict';

    const OrderReceipt = require('point_of_sale.OrderReceipt')
    const Registries = require('point_of_sale.Registries');

    const OrderReceiptGCC = OrderReceipt =>
        class extends OrderReceipt {

            get receiptEnv() {
                let receipt_render_env = super.receiptEnv;
                let receipt = receipt_render_env.receipt;
                receipt.is_gcc_country = ['SA', 'AE', 'BH', 'OM', 'QA', 'KW'].includes(receipt_render_env.order.pos.company.country.code);
                return receipt_render_env;
            }
        }
    Registries.Component.extend(OrderReceipt, OrderReceiptGCC)
    return OrderReceiptGCC
});
