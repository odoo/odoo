odoo.define('point_of_sale.OrderSummary', function(require) {
    'use strict';

    const { PosComponent } = require('point_of_sale.PosComponent');

    class OrderSummary extends PosComponent {
        constructor() {
            super(...arguments);
            this.order = this.props.order;
            this.update();
        }
        mounted() {
            this.order.orderlines.on('change', () => {
                this.update();
            });
        }
        update() {
            const total = this.order ? this.order.get_total_with_tax() : 0;
            const tax = this.order ? total - this.order.get_total_without_tax() : 0;
            this.total = this.env.pos.format_currency(total);
            this.tax = this.env.pos.format_currency(tax);
        }
    }

    return { OrderSummary };
});
