odoo.define('point_of_sale.BillScreen', function(require) {
    'use strict';

    const Registry = require('point_of_sale.ComponentsRegistry');

    const BillScreen = ReceiptScreen =>
        class extends ReceiptScreen {
            static template = 'BillScreen';
            confirm() {
                this.props.resolve({ confirmed: true, payload: null });
                this.trigger('close-temp-screen');
            }
        };

    Registry.addByExtending('BillScreen', 'ReceiptScreen', BillScreen);
});
