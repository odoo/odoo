/** @odoo-module */

import publicWidget from 'web.public.widget';

publicWidget.registry.websiteSaleDelivery.include({
    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _handleCarrierUpdateResult: async function (result) {
        await this._super.apply(this, arguments);
        if (result.new_amount_delivery_discount) {
            // Update discount of the order
            const cart_summary_discount_line = document.querySelector('[data-reward-type="shipping"]')
            if (cart_summary_discount_line) {
                cart_summary_discount_line.innerHTML = result.new_amount_delivery_discount;
            }
        }
        if (result.new_amount_delivery_discounted) {
            // Update discount of the order
            $('#order_delivery .monetary_field').html(result.new_amount_delivery_discounted);
        }
    },
});
