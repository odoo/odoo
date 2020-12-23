odoo.define('point_of_sale.OrderRow', function (require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');

    /**
     * @props {models.Order} order
     * @props columns
     * @emits click-order
     */
    class OrderRow extends PosComponent {
        get order() {
            return this.props.order;
        }
        get highlighted() {
            const highlightedOrder = this.props.highlightedOrder;
            return !highlightedOrder ? false : highlightedOrder.backendId === this.props.order.backendId;
        }

        // Column getters //

        get name() {
            return this.order.get_name();
        }
        get date() {
            return moment(this.order.validation_date).format('YYYY-MM-DD hh:mm A');
        }
        get customer() {
            const customer = this.order.get('client');
            return customer ? customer.name : null;
        }
        get total() {
            return this.env.pos.format_currency(this.order.get_total_with_tax());
        }
    }
    OrderRow.template = 'OrderRow';

    Registries.Component.add(OrderRow);

    return OrderRow;
});
