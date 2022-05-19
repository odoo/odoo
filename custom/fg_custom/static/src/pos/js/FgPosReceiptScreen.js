odoo.define('fg_custom.ReceiptScreen', function(require) {
    'use strict';

    const ReceiptScreen = require('point_of_sale.ReceiptScreen');
    const Registries = require('point_of_sale.Registries');

    var models = require('point_of_sale.models');

    const _super_posmodel = models.PosModel.prototype;
    const PosResReceiptScreen = ReceiptScreen =>
        class extends ReceiptScreen {
            /**
             * @override
             */

            async printReceipt() {
                var isPrinted = await super._printReceipt();
                this.currentOrder._printed = false;
                if(isPrinted && !this.currentOrder.x_receipt_printed){
                    this.currentOrder.x_receipt_printed = true;
                    this.currentOrder.trigger('change', this.currentOrder); // needed so that export_to_JSON gets triggered
                    this.currentOrder.x_receipt_printed_date = new Date();
                    this.render();
                    this.currentOrder.save_to_db();
                    this.env.pos.push_orders(this.currentOrder, {});
                }
                const isPrinted1 = await this._printReceipt();
                if (isPrinted1) {
                    this.currentOrder._printed = true;
                }
            }
        };

    Registries.Component.extend(ReceiptScreen, PosResReceiptScreen);

    return ReceiptScreen;
});


