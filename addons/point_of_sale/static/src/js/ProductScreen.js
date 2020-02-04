odoo.define('point_of_sale.ProductScreen', function(require) {
    'use strict';

    const { PosComponent } = require('point_of_sale.PosComponent');
    const { Chrome } = require('point_of_sale.chrome');
    const { ProductsWidget } = require('point_of_sale.ProductsWidget');
    const { OrderWidget } = require('point_of_sale.OrderWidget');
    const { NumpadWidget } = require('point_of_sale.NumpadWidget');
    const { ActionpadWidget } = require('point_of_sale.ActionpadWidget');
    const { NumpadState } = require('point_of_sale.models');

    class ProductScreen extends PosComponent {
        constructor() {
            super(...arguments);
            this.pos = this.props.pos;
            this.gui = this.props.gui;
            this.numpadState = new NumpadState();
        }
        mounted() {
            this.pos.on(
                'change:selectedOrder',
                () => {
                    this.render();
                },
                this
            );
        }
        willUnmount() {
            this.pos.off('change:selectedOrder', null, this);
        }
        clickProduct(event) {
            const product = event.detail;
            if (product.to_weight && this.pos.config.iface_electronic_scale) {
                this.gui.show_screen('scale', { product: product });
            } else {
                this.pos.get_order().add_product(product);
            }
        }
    }
    ProductScreen.components = { ProductsWidget, OrderWidget, NumpadWidget, ActionpadWidget };
    // TODO jcb: This is the way to add control buttons above the numpad
    ProductScreen.addControlButton = () => {};

    Chrome.addComponents([ProductScreen]);

    return { ProductScreen };
});
