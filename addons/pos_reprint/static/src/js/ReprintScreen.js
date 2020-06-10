odoo.define('pos_reprint.ReprintScreen', function (require) {
    'use strict';

    const ReceiptScreen = require('point_of_sale.ReceiptScreen');
    const Registries = require('point_of_sale.Registries');

    const ReprintScreen = (ReceiptScreen) => {
        class ReprintScreen extends ReceiptScreen {
            confirm() {
                this.props.resolve();
                // old order may be reprinted but
                // the current is still open
                this.currentOrder._printed = false;
                this.trigger('close-temp-screen');
            }
        }
        ReprintScreen.template = 'ReprintScreen';
        return ReprintScreen;
    };

    Registries.Component.addByExtending(ReprintScreen, ReceiptScreen);

    return ReprintScreen;
});
