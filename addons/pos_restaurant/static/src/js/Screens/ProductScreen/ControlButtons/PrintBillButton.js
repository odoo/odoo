odoo.define('point_of_sale.PrintBillButton', function(require) {
    'use strict';

    const { PosComponent } = require('point_of_sale.PosComponent');
    const { ProductScreen } = require('point_of_sale.ProductScreen');
    const { useListener } = require('web.custom_hooks');
    const Registry = require('point_of_sale.ComponentsRegistry');

    class PrintBillButton extends PosComponent {
        static template = 'PrintBillButton';
        constructor() {
            super(...arguments);
            useListener('click', this.onClick);
        }
        async onClick() {
            const order = this.env.pos.get_order();
            if (order.get_orderlines().length > 0) {
                await this.showTempScreen('BillScreen');
            } else {
                await this.showPopup('ErrorPopup', {
                    title: this.env._t('Nothing to Print'),
                    body: this.env._t('There are no order lines'),
                });
            }
        }
    }

    ProductScreen.addControlButton({
        component: PrintBillButton,
        condition: function() {
            return this.env.pos.config.iface_printbill;
        },
    });

    Registry.add('PrintBillButton', PrintBillButton);

    return { PrintBillButton };
});
