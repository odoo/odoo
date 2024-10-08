import WebsiteSaleCheckout from '@website_sale/js/checkout';

WebsiteSaleCheckout.include({

    /**
     * @override
     */
    _updateCartSummary(result) {
        this._super.apply(this, arguments);
        if (result.amount_delivery_discounted) {
            // Update discount of the order
            const cart_summary_delivery_discount_line = document.querySelector(
                '[data-reward-type="shipping"]'
            )
            if (cart_summary_delivery_discount_line) {
                cart_summary_delivery_discount_line.innerHTML = result.amount_delivery_discounted;
            }
        }
        if (result.amount_discounted) {
            // Update discount of the order
            const cart_summary_discount_line = document.querySelector(
                '#order_discount .monetary_field'
            );
            if (cart_summary_discount_line) {
                cart_summary_discount_line.innerHTML = result.amount_delivery_discounted;
            }
        }
    },
});
