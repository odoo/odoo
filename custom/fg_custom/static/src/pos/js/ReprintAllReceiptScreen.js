odoo.define('point_of_sale.ReprintAllReceiptScreen', function (require) {
    'use strict';

    const AbstractReceiptScreen = require('point_of_sale.AbstractReceiptScreen');
    const Registries = require('point_of_sale.Registries');

    const ReprintAllReceiptScreen = (AbstractReceiptScreen) => {
        class ReprintAllReceiptScreen extends AbstractReceiptScreen {
            mounted() {
                this.printReceipt();
            }
            confirm() {
                this.showScreen('TicketScreen', { reuseSavedUIState: true });
            }
            async printReceipt() {
                if(this.env.pos.proxy.printer && this.env.pos.config.iface_print_skip_screen) {
                    let result = await this._printReceipt();
                    if(result)
                        this.showScreen('TicketScreen', { reuseSavedUIState: true });
                }
            }
            async tryReprint() {
                await this._printReceipt();
            }
        }
        ReprintAllReceiptScreen.template = 'ReprintAllReceiptScreen';
        return ReprintAllReceiptScreen;
    };
    Registries.Component.addByExtending(ReprintAllReceiptScreen, AbstractReceiptScreen);

    return ReprintAllReceiptScreen;
});
