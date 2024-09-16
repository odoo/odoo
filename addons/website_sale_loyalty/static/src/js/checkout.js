import websiteSaleCheckout from '@website_sale/js/checkout';

websiteSaleCheckout.include({

    /**
     * @override
     */
    _updateCartSummary(result) {
        this._super.apply(this, arguments);
        if (result.amount_delivery_discounted) {
            // Update discount of the order
            const cart_summary_shipping_reward = document.querySelector(
                '[data-reward-type="shipping"]'
            )
            if (cart_summary_shipping_reward) {
                cart_summary_shipping_reward.innerHTML = result.amount_delivery_discounted;
            }
        }
        if (result.amount_order_discounted) {
            const cart_summary_discount_reward = document.querySelector(
                "[data-reward-type=discount]"
            );
            if (cart_summary_discount_reward) {
                cart_summary_discount_reward.innerHTML = result.amount_order_discounted;
            }
        }
    },
});
