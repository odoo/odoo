odoo.define('point_of_sale.OrderSummary', function(require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');
    const { float_is_zero } = require('web.utils');

    class OrderSummary extends PosComponent {
        getTotal() {
            return this.env.pos.format_currency(this.props.order.get_total_with_tax());
        }
        getTax() {
            const total = this.props.order.get_total_with_tax();
            const totalWithoutTax = this.props.order.get_total_without_tax();
            const taxAmount = total - totalWithoutTax;
            return {
                hasTax: !float_is_zero(taxAmount, this.env.pos.currency.decimal_places),
                displayAmount: this.env.pos.format_currency(taxAmount),
            };
        }
    }
    OrderSummary.template = 'OrderSummary';

    Registries.Component.add(OrderSummary);

    return OrderSummary;
});
