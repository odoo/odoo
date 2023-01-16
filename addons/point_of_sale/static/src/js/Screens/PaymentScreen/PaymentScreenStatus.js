/** @odoo-module */

import { PosComponent } from "@point_of_sale/js/PosComponent";

export class PaymentScreenStatus extends PosComponent {
    static template = "PaymentScreenStatus";

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
