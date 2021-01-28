odoo.define('pos_discount.DiscountButton', function(require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const ProductScreen = require('point_of_sale.ProductScreen');
    const { useListener } = require('web.custom_hooks');
    const Registries = require('point_of_sale.Registries');

    class DiscountButton extends PosComponent {
        constructor() {
            super(...arguments);
            useListener('click', this.onClick);
        }
        async onClick() {
            var self = this;
            const { confirmed, payload } = await this.showPopup('NumberPopup',{
                title: this.env._t('Discount Percentage'),
                startingValue: this.env.pos.config.discount_pc,
            });
            if (confirmed) {
                const val = Math.round(Math.max(0,Math.min(100,parseFloat(payload))));
                await self.apply_discount(val);
            }
        }
        async apply_discount(pc) {
            var order    = this.env.pos.get_order();
            var lines    = order.get_orderlines();
            for (const line of lines) {
                // Don't just set the discount, stack it to the existing one.
                // E.g. current discount = 20%, global discount to apply = 30%
                // Price calculation will be = price * (1 - 0.20) * (1 - 0.30)
                //
                // But in an orderline, there can be only one discount, so we compute
                // the 'net' discount before setting.
                // (1 - prev) * (1 - new) = 1 - prev - new + prev * new
                // If we pattern this to `total price = price * (1 - netdiscount)`,
                // netdiscount = prev + new - prev * new;
                //
                // In above example, the net discount will be 0.2 + 0.3 - 0.06 = 0.44
                const _prev = line.get_discount() / 100;
                const _new = pc / 100;
                const netdiscount = Math.round((_prev + _new - _prev * _new) * 100);
                line.set_discount(netdiscount);
            }
        }
    }
    DiscountButton.template = 'DiscountButton';

    ProductScreen.addControlButton({
        component: DiscountButton,
        condition: function() {
            return this.env.pos.config.module_pos_discount;
        },
    });

    Registries.Component.add(DiscountButton);

    return DiscountButton;
});
