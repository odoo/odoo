odoo.define('fg_custom.ReprintReceiptScreen', function(require) {
    'use strict';

    const ReprintReceiptScreen = require('point_of_sale.ReprintReceiptScreen');
    const Registries = require('point_of_sale.Registries');

    var models = require('point_of_sale.models');

    const _super_posmodel = models.PosModel.prototype;
    const PosResReceiptScreen = ReprintReceiptScreen =>
        class extends ReprintReceiptScreen {
            /**
             * @override
             */
            async tryReprint() {
                var isPrinted = await super._printReceipt();
                if(isPrinted && !this.props.order.x_receipt_printed){
                    this.props.order.x_receipt_printed = true;
                    this.props.order.x_receipt_printed_date = new Date();
                    this.props.order.trigger('change', this.props.order); // needed so that export_to_JSON gets triggered
                    this.render();
                    this.props.order.save_to_db();
                    this.env.pos.push_orders(this.props.order, {});
                }
            }
        };

    Registries.Component.extend(ReprintReceiptScreen, PosResReceiptScreen);

    return ReprintReceiptScreen;
});


