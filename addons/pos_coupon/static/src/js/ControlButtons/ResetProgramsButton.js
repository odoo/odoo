odoo.define('pos_coupon.ResetProgramsButton', function (require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const ProductScreen = require('point_of_sale.ProductScreen');
    const { useListener } = require('web.custom_hooks');
    const Registries = require('point_of_sale.Registries');

    class ResetProgramsButton extends PosComponent {
        constructor() {
            super(...arguments);
            useListener('click', this.onClick);
        }
        async onClick() {
            const order = this.env.pos.get_order();
            order.resetPrograms();
            this.trigger('close-popup');
        }
    }
    ResetProgramsButton.template = 'ResetProgramsButton';

    ProductScreen.addControlButton({
        component: ResetProgramsButton,
        condition: function () {
            return this.env.pos.config.use_coupon_programs;
        },
    });

    Registries.Component.add(ResetProgramsButton);

    return ResetProgramsButton;
});
