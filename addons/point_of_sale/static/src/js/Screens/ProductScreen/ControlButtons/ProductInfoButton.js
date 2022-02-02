odoo.define('point_of_sale.ProductInfoButton', function(require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const ProductScreen = require('point_of_sale.ProductScreen');
    const { useListener } = require("@web/core/utils/hooks");
    const Registries = require('point_of_sale.Registries');

    class ProductInfoButton extends PosComponent {
        setup() {
            super.setup();
            useListener('click', this.onClick);
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
