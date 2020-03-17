odoo.define('point_of_sale.SubmitOrderButton', function(require) {
    'use strict';

    const { PosComponent } = require('point_of_sale.PosComponent');
    const { ProductScreen } = require('point_of_sale.ProductScreen');
    const { useListener } = require('web.custom_hooks');
    const Registry = require('point_of_sale.ComponentsRegistry');

    class SubmitOrderButton extends PosComponent {
        static template = 'SubmitOrderButton';
        constructor() {
            super(...arguments);
            useListener('click', this.onClick);
        }
        async onClick() {
            const order = this.env.pos.get_order();
            if (order.hasChangesToPrint()) {
                await order.printChanges();
                order.saveChanges();
            }
        }
    }

    ProductScreen.addControlButton({
        component: SubmitOrderButton,
        condition: function() {
            return this.env.pos.printers.length;
        },
    });

    Registry.add('SubmitOrderButton', SubmitOrderButton);

    return { SubmitOrderButton };
});
