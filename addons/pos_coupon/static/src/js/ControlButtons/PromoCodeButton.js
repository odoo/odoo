odoo.define('pos_coupon.PromoCodeButton', function (require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const ProductScreen = require('point_of_sale.ProductScreen');
    const { useListener } = require('web.custom_hooks');
    const Registries = require('point_of_sale.Registries');

    class PromoCodeButton extends PosComponent {
        constructor() {
            super(...arguments);
            useListener('click', this.onClick);
        }
        async onClick() {
            const { confirmed, payload: code } = await this.showPopup('TextInputPopup', {
                title: this.env._t('Enter Promotion or Coupon Code'),
                startingValue: '',
            });
            if (confirmed && code !== '') {
                const order = this.env.pos.get_order();
                order.activateCode(code);
            }
        }
    }
    PromoCodeButton.template = 'PromoCodeButton';

    ProductScreen.addControlButton({
        component: PromoCodeButton,
        condition: function () {
            return this.env.pos.config.use_coupon_programs;
        },
    });

    Registries.Component.add(PromoCodeButton);

    return PromoCodeButton;
});
