odoo.define('pos_restaurant.TransferOrderButton', function(require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
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
    Registries.Component.add(TransferOrderButton);

    return TransferOrderButton;
});
