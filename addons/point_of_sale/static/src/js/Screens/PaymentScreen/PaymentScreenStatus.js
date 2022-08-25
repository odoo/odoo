odoo.define('point_of_sale.PaymentScreenStatus', function(require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');

    class PaymentScreenStatus extends PosComponent {
        get changeText() {
            return this.env.pos.format_currency(this.props.order.get_change());
        }
        get totalDueText() {
            return this.env.pos.format_currency(
                this.props.order.get_total_with_tax() + this.props.order.get_rounding_applied()
            );
        }
        get remainingText() {
            return this.env.pos.format_currency(
                this.props.order.get_due() > 0 ? this.props.order.get_due() : 0
            );
        }
    }
    PaymentScreenStatus.template = 'PaymentScreenStatus';

    Registries.Component.add(PaymentScreenStatus);

    return PaymentScreenStatus;
});
