odoo.define('pos_restaurant.BillScreen', function (require) {
    'use strict';

    const ReceiptScreen = require('point_of_sale.ReceiptScreen');
    const Registries = require('point_of_sale.Registries');

    const BillScreen = (ReceiptScreen) => {
        class BillScreen extends ReceiptScreen {
            confirm() {
                this.props.resolve({ confirmed: true, payload: null });
                this.trigger('close-temp-screen');
            }
            whenClosing() {
                this.confirm();
            }
            /**
             * @override
             */
            async printReceipt() {
                const currentOrder = this.currentOrder;
                await super.printReceipt();
                currentOrder._printed = false;
            }
        }
        BillScreen.template = 'BillScreen';
        return BillScreen;
    };

    Registries.Component.addByExtending(BillScreen, ReceiptScreen);

    return BillScreen;
});
