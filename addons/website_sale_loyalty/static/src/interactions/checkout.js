import { setElementContent } from '@web/core/utils/html';
import { patch } from '@web/core/utils/patch';
import { Checkout } from '@website_sale/interactions/checkout';

patch(Checkout.prototype, {
    /**
     * @override method from `@website_sale/interactions/checkout`
     */
    _updateCartSummary(result, targetEl) {
        super._updateCartSummary(...arguments);
        if (result.amount_delivery_discounted) {
            // Update discount of the order
            const cart_summary_shipping_reward = targetEl.querySelector(
                '[data-reward-type="shipping"]'
            );
            if (cart_summary_shipping_reward) {
                setElementContent(cart_summary_shipping_reward, result.amount_delivery_discounted);
            }
        }
        if (result.discount_reward_amounts) {
            const cart_summary_discount_rewards = targetEl.querySelectorAll(
                '[data-reward-type=discount]'
            );
            if (cart_summary_discount_rewards.length !== result.discount_reward_amounts.length) {
                // refresh cart summary to sync number of discount items
                location.reload();
            } else {
                cart_summary_discount_rewards.forEach(
                    (el, i) => (setElementContent(el, result.discount_reward_amounts[i]))
                );
            }
        }
    },
});
