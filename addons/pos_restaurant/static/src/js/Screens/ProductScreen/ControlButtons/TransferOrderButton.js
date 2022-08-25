odoo.define('pos_restaurant.TransferOrderButton', function(require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const ProductScreen = require('point_of_sale.ProductScreen');
    const { useListener } = require("@web/core/utils/hooks");
    const Registries = require('point_of_sale.Registries');

    class TransferOrderButton extends PosComponent {
        setup() {
            super.setup();
            useListener('click', this.onClick);
        }
        async onClick() {
            this.env.pos.setCurrentOrderToTransfer();
            this.showScreen('FloorScreen');
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
