/** @odoo-module **/

import publicWidget from 'web.public.widget';

publicWidget.registry.websiteSaleDelivery.include({
    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _handleCarrierUpdateResult: async function (carrierInput) {
        await this._super.apply(this, arguments);
        if (this.result.new_amount_delivery_discount) {
            // Update amount of the free shipping line
            const cart_summary_discount_line = document.querySelector(
                '[data-reward-type="shipping"]'
            );
            if (cart_summary_discount_line) {
                cart_summary_discount_line.innerHTML = this.result.new_amount_delivery_discount;
            }
        }
    },
});
