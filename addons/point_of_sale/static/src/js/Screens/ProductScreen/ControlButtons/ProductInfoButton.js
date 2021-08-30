odoo.define('point_of_sale.ProductInfoButton', function(require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const ProductScreen = require('point_of_sale.ProductScreen');
    const { useListener } = require('web.custom_hooks');
    const Registries = require('point_of_sale.Registries');

    class ProductInfoButton extends PosComponent {
        constructor() {
            super(...arguments);
            useListener('click', this.onClick);
        }
        mounted() {
            this.env.pos.get('orders').on('add remove change', () => this.render(), this);
            this.env.pos.on('change:selectedOrder', () => this.render(), this);
        }
        willUnmount() {
            this.env.pos.get('orders').off('add remove change', null, this);
            this.env.pos.off('change:selectedOrder', null, this);
        }
        onClick() {
            const orderline = this.env.pos.get_order().get_selected_orderline();
            if (orderline) {
                const product = orderline.get_product();
                const quantity = orderline.get_quantity();
                this.showPopup('ProductInfoPopup', { product, quantity });
            }
        }
    }
    ProductInfoButton.template = 'ProductInfoButton';

    ProductScreen.addControlButton({
        component: ProductInfoButton,
        condition: () => true,
        position: ['before', 'SetFiscalPositionButton'],
    });

    Registries.Component.add(ProductInfoButton);

    return ProductInfoButton;
});
