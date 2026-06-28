import { Component } from "@odoo/owl";
import { formatCurrency } from "@web/core/currency";

export class PromotionProgressBar extends Component {
    static template = "website_sale_loyalty.PromotionProgressBar";
    static props = {
        reward_name: String,
        minimum_amount: Number,
        progress: Number,
        currency_id: Number,
    };

    getFormattedMinAmount() {
        return formatCurrency(this.props.minimum_amount, this.props.currency_id);
    }
}
