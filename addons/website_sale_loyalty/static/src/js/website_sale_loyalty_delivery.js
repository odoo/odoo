/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";


publicWidget.registry.websiteSaleDelivery.include({
    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    async _handleCarrierUpdateResult(carrierInput) {
        await this._super(...arguments);
        if (this.result.new_amount_delivery_discount) {
            // Update amount of the free shipping line
            const cart_summary_discount_line = document.querySelector(
                '[data-reward-type="shipping"]'
            );
            if (cart_summary_discount_line) {
                cart_summary_discount_line.innerHTML = this.result.new_amount_delivery_discount;
            }
        }
        else if (this.result.new_amount_order_discounted) {
             const cart_summary_discount_line = document.querySelector(
                '[data-reward-type="discount"]'
            );
            if (cart_summary_discount_line) {
                cart_summary_discount_line.innerHTML = this.result.new_amount_order_discounted;
            }
        }
    },
});
