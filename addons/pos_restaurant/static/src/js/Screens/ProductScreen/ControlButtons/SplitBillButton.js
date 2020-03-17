odoo.define('point_of_sale.SplitBillButton', function(require) {
    'use strict';

    const { PosComponent } = require('point_of_sale.PosComponent');
    const { ProductScreen } = require('point_of_sale.ProductScreen');
    const { useListener } = require('web.custom_hooks');
    const Registry = require('point_of_sale.ComponentsRegistry');

    class SplitBillButton extends PosComponent {
        static template = 'SplitBillButton';
        constructor() {
            super(...arguments);
            useListener('click', this.onClick);
        }
        async onClick() {
            const order = this.env.pos.get_order();
            if (order.get_orderlines().length > 0) {
                this.showScreen('SplitBillScreen');
            }
        }
    }

    ProductScreen.addControlButton({
        component: SplitBillButton,
        condition: function() {
            return this.env.pos.config.iface_splitbill;
        },
    });

    Registry.add('SplitBillButton', SplitBillButton);

    return { SplitBillButton };
});
