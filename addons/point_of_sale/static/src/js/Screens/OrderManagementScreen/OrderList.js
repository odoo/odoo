odoo.define('point_of_sale.OrderList', function (require) {
    'use strict';

    const { useState } = owl.hooks;
    const { useListener } = require('web.custom_hooks');
    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');

    /**
     * @props {models.Order} [initHighlightedOrder] initially highligted order
     * @props {Array<models.Order>} orders
     */
    class OrderList extends PosComponent {
        constructor() {
            super(...arguments);
            useListener('click-order', this._onClickOrder);
            this.state = useState({ highlightedOrder: this.props.initHighlightedOrder || null });
        }
        get highlightedOrder() {
            return this.state.highlightedOrder;
        }
        _onClickOrder({ detail: order }) {
            this.state.highlightedOrder = order;
        }
    }
    OrderList.template = 'OrderList';

    Registries.Component.add(OrderList);

    return OrderList;
});
