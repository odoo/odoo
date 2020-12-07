odoo.define('pos_discount.DiscountButton', function (require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const { useListener } = require('web.custom_hooks');

    class DiscountButton extends PosComponent {
        constructor() {
            super(...arguments);
            useListener('click', this.onClick);
        }
        async onClick() {
            const [confirmed, payload] = await this.env.ui.askUser('NumberPopup', {
                title: this.env._t('Discount Percentage'),
                startingValue: this.env.model.config.discount_pc,
                isInputSelected: true,
            });
            if (confirmed) {
                const val = Math.round(Math.max(0, Math.min(100, parseFloat(payload))));
                await this.env.model.actionHandler({ name: 'actionApplyDiscount', args: [this.props.activeOrder, val] });
            }
        }
    }
    DiscountButton.template = 'pos_discount.DiscountButton';

    return DiscountButton;
});
