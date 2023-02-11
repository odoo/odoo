odoo.define('pos_restaurant.PrintBillButton', function(require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const ProductScreen = require('point_of_sale.ProductScreen');
    const { useListener } = require('web.custom_hooks');
    const Registries = require('point_of_sale.Registries');

    class PrintBillButton extends PosComponent {
        constructor() {
            super(...arguments);
            useListener('click', this.onClick);
        }
        async onClick() {
            const order = this.env.pos.get_order();
            if (order.get_orderlines().length > 0) {
                order.initialize_validation_date();
                this.trigger('close-popup');
                await this.showTempScreen('BillScreen');
            } else {
                await this.showPopup('ErrorPopup', {
                    title: this.env._t('Nothing to Print'),
                    body: this.env._t('There are no order lines'),
                });
            }
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
