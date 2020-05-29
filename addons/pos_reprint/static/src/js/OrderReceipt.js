odoo.define('pos_reprint.OrderReceipt', function(require) {
    'use strict';

    const OrderReceipt = require('point_of_sale.OrderReceipt');
    const Registries = require('point_of_sale.Registries');

    const PosReprintOrderReceipt = OrderReceipt =>
        class extends OrderReceipt {
            get receiptEnv () {
              if (this.props.isReprint) {
                return this.env.pos.last_receipt_render_env;
              }
              else {
                  const receipt_render_env = super.receiptEnv;
                  this.env.pos.last_receipt_render_env = receipt_render_env;
                  return receipt_render_env;
              }
            }
        };

    Registries.Component.extend(OrderReceipt, PosReprintOrderReceipt);

    return OrderReceipt;
});
