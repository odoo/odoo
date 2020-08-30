odoo.define('point_of_sale.ReprintReceiptScreen', function (require) {
    'use strict';

    const AbstractReceiptScreen = require('point_of_sale.AbstractReceiptScreen');
    const Registries = require('point_of_sale.Registries');

    const ReprintReceiptScreen = (AbstractReceiptScreen) => {
        class ReprintReceiptScreen extends AbstractReceiptScreen {
            confirm() {
                this.props.resolve({ confirmed: true, payload: null });
                this.trigger('close-temp-screen');
            }
            tryReprint() {
                this._printReceipt();
            }
        }
        ReprintReceiptScreen.template = 'ReprintReceiptScreen';
        return ReprintReceiptScreen;
    };
    Registries.Component.addByExtending(ReprintReceiptScreen, AbstractReceiptScreen);

    return ReprintReceiptScreen;
});
