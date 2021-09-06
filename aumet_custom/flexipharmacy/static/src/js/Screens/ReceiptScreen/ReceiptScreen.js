odoo.define('flexipharmacy.ReceiptScreen', function(require) {
    'use strict';

    const ReceiptScreen = require('point_of_sale.ReceiptScreen');
    const Registries = require('point_of_sale.Registries');

    const AsplRetReceiptScreenInh = ReceiptScreen =>
        class extends ReceiptScreen {
            constructor() {
                super(...arguments);
            }
            orderDone() {
                super.orderDone(...arguments);
                if(this.env.pos.config.customer_display){
                    this.currentOrder.mirror_image_data();
                }
            }
            clickBack() {
                this.showScreen('ProductScreen');
            }
        };

    Registries.Component.extend(ReceiptScreen, AsplRetReceiptScreenInh);

    return ReceiptScreen;
});