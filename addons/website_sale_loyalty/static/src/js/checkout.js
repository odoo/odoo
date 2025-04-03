import { markup } from "@odoo/owl";
import { setElementContent } from "@web/core/utils/html";
import WebsiteSaleCheckout from '@website_sale/js/checkout';

WebsiteSaleCheckout.include({
    /** @override */
    async _setDeliveryMethod() {
        const result = await this._super.apply(this, arguments);
        // markup: discount_reward_amounts is coming from Monetary.value_to_html in _order_summary_values
        result.discount_reward_amounts = result.discount_reward_amounts.map(
            (discount_reward_amount) => markup(discount_reward_amount)
        );
        return result;
    },
    /**
     * @override
     */
    _updateCartSummary(result) {
        this._super.apply(this, arguments);
        if (result.amount_delivery_discounted) {
            // Update discount of the order
            const cart_summary_shipping_reward = document.querySelector(
                '[data-reward-type="shipping"]'
            );
            if (cart_summary_shipping_reward) {
                setElementContent(cart_summary_shipping_reward, result.amount_delivery_discounted);
            }
        }
        if (result.discount_reward_amounts) {
            const cart_summary_discount_rewards = document.querySelectorAll(
                '[data-reward-type=discount]'
            );
            if (cart_summary_discount_rewards.length !== result.discount_reward_amounts.length) {
                // refresh cart summary to sync number of discount items
                location.reload();
            } else {
                cart_summary_discount_rewards.forEach((el, i) =>
                    setElementContent(el, result.discount_reward_amounts[i])
                );
            }
        }
    },
});
