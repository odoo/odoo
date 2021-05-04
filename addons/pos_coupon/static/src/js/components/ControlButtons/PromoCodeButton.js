odoo.define('pos_coupon.PromoCodeButton', function (require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const { useListener } = require('web.custom_hooks');

    class PromoCodeButton extends PosComponent {
        constructor() {
            super(...arguments);
            useListener('click', this.onClick);
        }
        async onClick() {
            const [confirmed, code] = await this.env.ui.askUser('TextInputPopup', {
                title: this.env._t('Enter Promotion or Coupon Code'),
                startingValue: '',
            });
            if (confirmed && code !== '') {
                await this.env.model.actionHandler({ name: 'actionActivateCode', args: [this.props.activeOrder, code] });
            }
        }
    }
    PromoCodeButton.template = 'pos_coupon.PromoCodeButton';

    return PromoCodeButton;
});
