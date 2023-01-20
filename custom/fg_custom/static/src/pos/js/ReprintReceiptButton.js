odoo.define('fg_custom.ReprintReceiptButton', function(require) {
    'use strict';

    const Registries = require('point_of_sale.Registries');
    const ReprintReceiptButton = require('point_of_sale.ReprintReceiptButton');

    const FgReprintReceiptButton = ReprintReceiptButton =>
        class extends ReprintReceiptButton {
            async _onClick() {
                await super._onClick();
                if(this.props && this.props.order && this.props.order.backendId){
                    await this.rpc({
                        model: 'transaction.log',
                        method: 'create_transaction_log',
                        args: [, 'reprint_receipt', 'pos.order', this.props.order.backendId],
                    });
                }
            }
        };

    Registries.Component.extend(ReprintReceiptButton, FgReprintReceiptButton);
    return FgReprintReceiptButton;
});
