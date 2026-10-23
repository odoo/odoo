import { markup } from '@odoo/owl';
import { patch } from '@web/core/utils/patch';
import { Checkout } from '@website_sale/interactions/checkout';

patch(Checkout.prototype, {
    /**
     * @override method from `@website_sale/interactions/checkout`
     */
    _markupOrderSummaryValues(values) {
        values = super._markupOrderSummaryValues(...arguments);
        if (values.amount_delivery_discounted) {
            values.amount_delivery_discounted = markup(values.amount_delivery_discounted);
        }
        if (values.discount_reward_amounts) {
            values.discount_reward_amounts = values.discount_reward_amounts.map(
                (amount) => markup(amount)
            );
        }
        return values;
    },
});
