odoo.define('pos_restaurant.BillScreen', function (require) {
    'use strict';

    const ReceiptScreen = require('point_of_sale.ReceiptScreen');

    class BillScreen extends ReceiptScreen {
        confirm() {
            this.props.resolve();
            this.trigger('close-temp-screen');
        }
        onOrderDone() {
            this.confirm();
        }
    }
    BillScreen.template = 'pos_restaurant.BillScreen';

    return BillScreen;
});
