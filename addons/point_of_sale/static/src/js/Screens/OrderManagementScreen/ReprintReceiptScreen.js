odoo.define('point_of_sale.ReprintReceiptScreen', function (require) {
    'use strict';

    const AbstractReceiptScreen = require('point_of_sale.AbstractReceiptScreen');
    const Registries = require('point_of_sale.Registries');

    const ReprintReceiptScreen = (AbstractReceiptScreen) => {
        class ReprintReceiptScreen extends AbstractReceiptScreen {
            mounted() {
                this.tryReprint();
            }
            confirm() {
                this.showScreen('OrderManagementScreen');
            }
            async tryReprint() {
                if(this.env.pos.proxy.printer && this.env.pos.config.iface_print_skip_screen) {
                    let result = await this._printReceipt();
                    if(result)
                        this.showScreen('OrderManagementScreen');
                }
            }
        }
        ReprintReceiptScreen.template = 'ReprintReceiptScreen';
        return ReprintReceiptScreen;
    };
    Registries.Component.addByExtending(ReprintReceiptScreen, AbstractReceiptScreen);

    return ReprintReceiptScreen;
});
