odoo.define('pos_restaurant.SplitBillButton', function(require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const ProductScreen = require('point_of_sale.ProductScreen');
    const { useListener } = require("@web/core/utils/hooks");
    const Registries = require('point_of_sale.Registries');

    class SplitBillButton extends PosComponent {
        setup() {
            super.setup();
            useListener('click', this.onClick);
        }
        _isDisabled() {
            const order = this.env.pos.get_order();
            return order.get_orderlines().reduce((totalProduct, orderline) => totalProduct + orderline.quantity, 0) < 2;
        }
        async onClick() {
            this.showScreen('SplitBillScreen');
        }
    }
    SplitBillButton.template = 'SplitBillButton';

    ProductScreen.addControlButton({
        component: SplitBillButton,
        condition: function() {
            return this.env.pos.config.iface_splitbill;
        },
    });

    Registries.Component.add(SplitBillButton);

    return SplitBillButton;
});
