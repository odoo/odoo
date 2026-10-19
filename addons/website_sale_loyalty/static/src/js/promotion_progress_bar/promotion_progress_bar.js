import { Component, t, useProps } from "@odoo/owl";
import { formatCurrency } from "@web/core/currency";

export class PromotionProgressBar extends Component {
    static template = "website_sale_loyalty.PromotionProgressBar";
    props = useProps({
        reward_name: t.string(),
        minimum_amount: t.number(),
        progress: t.number(),
        currency_id: t.number(),
    });

    getFormattedMinAmount() {
        return formatCurrency(this.props.minimum_amount, this.props.currency_id);
    }
}
