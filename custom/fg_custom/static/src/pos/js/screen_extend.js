odoo.define('fg_custom.order_screen', function(require) {
    'use strict';

    const OrderReceipt = require('point_of_sale.OrderReceipt');
    const Registries = require('point_of_sale.Registries');
    var models = require('point_of_sale.models');

    const SiTransSequenceOrderReceipt = OrderReceipt =>
        class extends OrderReceipt {
            async willUpdateProps() {
                await super.willUpdateProps(...arguments);
                var order = this.env.pos.get_order();
                var old_name = order.name
                const data = await this._getSiTransSequence(old_name);
                this._receiptEnv.receipt.pos_trans_reference = data.pos_trans_reference;
                this._receiptEnv.receipt.pos_si_trans_reference = data.pos_si_trans_reference;
                this._receiptEnv.receipt.pos_refund_si_reference = data.pos_refund_si_reference;
                this._receiptEnv.receipt.pos_refunded_id = data.pos_refunded_id;
            }

            async _getSiTransSequence(name) {
                var self = this;
                const data = await this.rpc({
                    model: 'pos.order',
                    method: 'get_si_trans_sequence_number',
                    args: [0, name],
                });
                return data;
            }
        };

    Registries.Component.extend(OrderReceipt, SiTransSequenceOrderReceipt);
    return OrderReceipt;
});
