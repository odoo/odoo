odoo.define('pos_restaurant.PrintBillButton', function(require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const ProductScreen = require('point_of_sale.ProductScreen');
    const { useListener } = require("@web/core/utils/hooks");
    const Registries = require('point_of_sale.Registries');

    class PrintBillButton extends PosComponent {
        setup() {
            super.setup();
            useListener('click', this.onClick);
        }
        _isDisabled() {
            const order = this.env.pos.get_order();
            return order.get_orderlines().length === 0;
        }
        onClick() {
            this.showTempScreen('BillScreen');
        }
    }
    PrintBillButton.template = 'PrintBillButton';

    ProductScreen.addControlButton({
        component: PrintBillButton,
        condition: function() {
            return this.env.pos.config.iface_printbill;
        },
    });

    Registries.Component.add(PrintBillButton);

    return PrintBillButton;
});
