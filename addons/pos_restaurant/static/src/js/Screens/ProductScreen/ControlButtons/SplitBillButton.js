odoo.define('pos_restaurant.SplitBillButton', function (require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const { useListener } = require('web.custom_hooks');

    class SplitBillButton extends PosComponent {
        constructor() {
            super(...arguments);
            useListener('click', this.onClick);
        }
        async onClick() {
            const orderlines = this.env.model.getOrderlines(this.props.activeOrder);
            if (orderlines.length > 0) {
                await this.env.model.actionHandler({ name: 'actionShowScreen', args: ['SplitBillScreen'] });
            } else {
                this.env.ui.showNotification(this.env._t('Nothing to split.'));
            }
        }
    }
    SplitBillButton.template = 'pos_restaurant.SplitBillButton';

    return SplitBillButton;
});
