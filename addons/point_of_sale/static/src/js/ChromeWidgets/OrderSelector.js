odoo.define('point_of_sale.OrderSelector', function(require) {
    'use strict';

    const { Chrome } = require('point_of_sale.chrome');
    const { PosComponent, addComponents } = require('point_of_sale.PosComponent');
    const Registry = require('point_of_sale.ComponentsRegistry');

    // Previously OrderSelectorWidget
    class OrderSelector extends PosComponent {
        static template = 'OrderSelector';
        mounted() {
            this.env.pos.get('orders').on('add remove change', () => this.render(), this);
            this.env.pos.on('change:selectedOrder', () => this.render(), this);
        }
        willUnmount() {
            this.env.pos.get('orders').off('add remove change', null, this);
            this.env.pos.off('change:selectedOrder', null, this);
        }
        selectOrder(order) {
            this.env.pos.set_order(order);
        }
        addNewOrder() {
            this.env.pos.add_new_order();
        }
        get orderList() {
            return this.env.pos.get_order_list();
        }
        async deleteCurrentOrder() {
            const order = this.env.pos.get_order();
            if (!order) {
                return;
            } else if (!order.is_empty()) {
                const { confirmed } = await this.showPopup('ConfirmPopup', {
                    title: this.env._t('Destroy Current Order ?'),
                    body: this.env._t('You will lose any data associated with the current order'),
                });
                if (confirmed) this.env.pos.delete_current_order();
            } else {
                this.env.pos.delete_current_order();
            }
        }
        creationTime(order) {
            return moment(order.creation_date).format('hh:mm');
        }
    }

    addComponents(Chrome, [OrderSelector]);

    Registry.add('OrderSelector', OrderSelector);

    return { OrderSelector };
});
