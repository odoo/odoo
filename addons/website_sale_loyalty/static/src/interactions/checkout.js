import { patch } from '@web/core/utils/patch';
import { Checkout } from '@website_sale/interactions/checkout';

patch(Checkout.prototype, {
    /**
     * @override method from `@website_sale/interactions/checkout`
     */
    _updateCartSummaries(_result) {
        super._updateCartSummaries(...arguments);

        // Update discounts line in small cart
        for (const targetEl of document.querySelectorAll(
            "#o_cart_summary_offcanvas, div.o_total_card"
        )) {
            if (_result.amount_delivery_discounted) {
                // Update discount of the order
                const cart_summary_shipping_reward = targetEl.querySelector(
                    '[data-reward-type="shipping"]'
                );
                if (cart_summary_shipping_reward) {
                    cart_summary_shipping_reward.innerHTML = _result.amount_delivery_discounted;
                }
            }
            if (_result.discount_reward_amounts) {
                const cart_summary_discount_rewards = targetEl.querySelectorAll(
                    "[data-reward-type=discount]"
                );
                if (
                    cart_summary_discount_rewards.length !== _result.discount_reward_amounts.length
                ) {
                    // refresh cart summary to sync number of discount items
                    location.reload();
                } else {
                    cart_summary_discount_rewards.forEach(
                        (el, i) => (el.innerHTML = _result.discount_reward_amounts[i]),
                    );
                }
            }
        }
    },
});
