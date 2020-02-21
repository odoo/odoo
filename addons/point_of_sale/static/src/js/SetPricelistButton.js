odoo.define('point_of_sale.SetPricelistButton', function(require) {
    'use strict';

    const { PosComponent } = require('point_of_sale.PosComponent');
    const { ProductScreen } = require('point_of_sale.ProductScreen');
    const { useListener } = require('web.custom_hooks');

    class SetPricelistButton extends PosComponent {
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
        get currentPricelistName() {
            const order = this.env.pos.get_order();
            return order && order.pricelist
                ? order.pricelist.display_name
                : this.env._t('Pricelist');
        }
        onClick() {
            alert('SetPricelistButton clicked!');
        }
    }

    ProductScreen.addControlButton({
        component: SetPricelistButton,
        condition: function() {
            return this.env.pos.config.use_pricelist && this.env.pos.pricelists.length > 1;
        },
    });

    return { SetPricelistButton };
});
