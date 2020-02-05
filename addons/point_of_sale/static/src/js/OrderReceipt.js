odoo.define('point_of_sale.OrderReceipt', function(require) {
    'use strict';

    const { PosComponent } = require('point_of_sale.PosComponent');
    const {
        WrappedProductNameLines,
    } = require('point_of_sale.WrappedProductNameLines');

    class OrderReceipt extends PosComponent {
        constructor() {
            super(...arguments);
            this.pos = this.props.pos;
            this.receiptEnv = this.props.receiptEnv;
            this.order = this.receiptEnv.order;
            this.receipt = this.receiptEnv.receipt;
            this.orderlines = this.receiptEnv.orderlines;
            this.paymentlines = this.receiptEnv.paymentlines;
            this.isTaxIncluded =
                Math.abs(this.receipt.subtotal - this.receipt.total_with_tax) <= 0.000001;
        }
        isSimple(line) {
            return (
                line.discount === 0 &&
                line.unit_name === 'Units' &&
                line.quantity === 1 &&
                !(
                    line.display_discount_policy == 'without_discount' &&
                    line.price != line.price_lst
                )
            );
        }
    }
    OrderReceipt.components = { WrappedProductNameLines }

    return { OrderReceipt };
});
