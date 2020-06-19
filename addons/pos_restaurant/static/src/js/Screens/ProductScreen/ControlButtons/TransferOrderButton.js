odoo.define('pos_restaurant.TransferOrderButton', function(require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const ProductScreen = require('point_of_sale.ProductScreen');
    const { useListener } = require('web.custom_hooks');
    const Registries = require('point_of_sale.Registries');

    class TransferOrderButton extends PosComponent {
        constructor() {
            super(...arguments);
            useListener('click', this.onClick);
        }
        onClick() {
            this.env.pos.transfer_order_to_different_table();
        }
    }
    TransferOrderButton.template = 'TransferOrderButton';

    ProductScreen.addControlButton({
        component: TransferOrderButton,
        condition: function() {
            return this.env.pos.config.iface_floorplan;
        },
    });

    Registries.Component.add(TransferOrderButton);

    return TransferOrderButton;
});
