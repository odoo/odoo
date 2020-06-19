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
            var product  = this.env.pos.db.get_product_by_id(this.env.pos.config.discount_product_id[0]);
            if (product === undefined) {
                await this.showPopup('ErrorPopup', {
                    title : this.env._t("No discount product found"),
                    body  : this.env._t("The discount product seems misconfigured. Make sure it is flagged as 'Can be Sold' and 'Available in Point of Sale'."),
                });
                return;
            }

            // Remove existing discounts
            var i = 0;
            while ( i < lines.length ) {
                if (lines[i].get_product() === product) {
                    order.remove_orderline(lines[i]);
                } else {
                    i++;
                }
            }

            // Add discount
            // We add the price as manually set to avoid recomputation when changing customer.
            var base_to_discount = order.get_total_without_tax();
            if (product.taxes_id.length){
                var first_tax = this.pos.taxes_by_id[product.taxes_id[0]];
                if (first_tax.price_include) {
                    base_to_discount = order.get_total_with_tax();
                }
            }
            var discount = - pc / 100.0 * base_to_discount;

            if( discount < 0 ){
                order.add_product(product, {
                    price: discount,
                    lst_price: discount,
                    extras: {
                        price_manually_set: true,
                    },
                });
            }
        }
    }
    DiscountButton.template = 'DiscountButton';

    ProductScreen.addControlButton({
        component: DiscountButton,
        condition: function() {
            return this.env.pos.config.module_pos_discount && this.env.pos.config.discount_product_id;
        },
    });

    Registries.Component.add(DiscountButton);

    return DiscountButton;
});
