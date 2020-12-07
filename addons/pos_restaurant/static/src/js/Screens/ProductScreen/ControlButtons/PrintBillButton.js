odoo.define('pos_restaurant.PrintBillButton', function(require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const { useListener } = require('web.custom_hooks');

    class PrintBillButton extends PosComponent {
        constructor() {
            super(...arguments);
            useListener('click', this.onClick);
        }
        async onClick() {
            if (this.env.model.getOrderlines(this.props.activeOrder).length > 0) {
                await this.showTempScreen('BillScreen', { activeOrder: this.props.activeOrder });
            } else {
                await this.env.ui.askUser('ErrorPopup', {
                    title: this.env._t('Nothing to Print'),
                    body: this.env._t('There are no order lines'),
                });
            }
        }
    }
    PrintBillButton.template = 'pos_restaurant.PrintBillButton';

    return PrintBillButton;
});
