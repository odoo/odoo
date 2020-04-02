odoo.define('point_of_sale.OrderReceipt', function(require) {
    'use strict';

    const { PosComponent } = require('point_of_sale.PosComponent');
    const { WrappedProductNameLines } = require('point_of_sale.WrappedProductNameLines');
    const Registry = require('point_of_sale.ComponentsRegistry');

    class OrderReceipt extends PosComponent {
        static template = 'OrderReceipt';
        constructor() {
            super(...arguments);
            this.receiptEnv = this.props.order.getOrderReceiptEnv();
        }
        get receipt() {
            return this.receiptEnv.receipt;
        }
        get orderlines() {
            return this.receiptEnv.orderlines;
        }
        get paymentlines() {
            return this.receiptEnv.paymentlines;
        }
        get isTaxIncluded() {
            return Math.abs(this.receipt.subtotal - this.receipt.total_with_tax) <= 0.000001;
        }
        willUpdateProps(nextProps) {
            this.receiptEnv = nextProps.order.getOrderReceiptEnv();
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
    OrderReceipt.components = { WrappedProductNameLines };

    Registry.add('OrderReceipt', OrderReceipt);

    return { OrderReceipt };
});
