import { patch } from "@web/core/utils/patch";
import { redirect } from "@web/core/utils/urls";

import { ExpressCheckout } from "@payment/interactions/express_checkout";

patch(ExpressCheckout.prototype, {
    start() {
        super.start();
        // Monitor updates of the amount on eCommerce's cart pages.
        this.services.cart.bus.addEventListener("cart_amount_changed", (ev) =>
            this._updateAmount(...ev.detail)
        );
    },
    /**
     * Redirect the user if the checkout progress wasn't complete at the transaction creation.
     * @override
     */
    _handlePaymentProcessingError(processingValues) {
        if (processingValues.redirect) {
            redirect(processingValues.redirect);
        } else {
            super._handlePaymentProcessingError(processingValues);
        }
    },
});
