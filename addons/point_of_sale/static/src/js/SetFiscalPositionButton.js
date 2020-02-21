odoo.define('point_of_sale.SetFiscalPositionButton', function(require) {
    'use strict';

    const { PosComponent } = require('point_of_sale.PosComponent');
    const { ProductScreen } = require('point_of_sale.ProductScreen');
    const { useListener } = require('web.custom_hooks');

    class SetFiscalPositionButton extends PosComponent {
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
        get currentFiscalPositionName() {
            const order = this.env.pos.get_order();
            return order && order.fiscal_position
                ? order.fiscal_position.display_name
                : this.env._t('Tax');
        }
        onClick() {
            alert('SetFiscalPositionButton clicked!');
        }
    }

    ProductScreen.addControlButton({
        component: SetFiscalPositionButton,
        condition: function() {
            return this.env.pos.fiscal_positions.length > 0;
        },
        position: ['before', 'SetPricelistButton'],
    });

    return { SetFiscalPositionButton };
});
