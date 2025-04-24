import { patch } from '@web/core/utils/patch';
import { PaymentButton } from '@payment/interactions/payment_button';

patch(PaymentButton.prototype, {

    /**
     * Hide the disabled PayPal button and show the enabled one.
     *
     * @override method from @payment/interactions/payment_button
     * @private
     * @return {void}
     */
    _setEnabled() {
        if (!this.paymentButton.dataset.isPaypal) {
            super._setEnabled();
            return;
        }

        document.getElementById('o_paypal_disabled_button').classList.add('d-none');
        document.getElementById('o_paypal_enabled_button').classList.remove('d-none');
    },

    /**
     * Hide the enabled PayPal button and show the disabled one.
     *
     * @override method from @payment/interactions/payment_button
     * @private
     * @return {void}
     */
    _disable() {
        if (!this.paymentButton.dataset.isPaypal) {
            super._disable();
            return;
        }

        document.getElementById('o_paypal_disabled_button').classList.remove('d-none');
        document.getElementById('o_paypal_enabled_button').classList.add('d-none');
    },

    /**
     * Disable the generic behavior that would hide the PayPal button container.
     *
     * @override method from @payment/interactions/payment_button
     * @private
     * @return {void}
     */
    _hide() {
        if (!this.paymentButton.dataset.isPaypal) {
            super._hide();
        }
    },

    /**
     * Disable the generic behavior that would show the PayPal button container.
     *
     * @override method from @payment/interactions/payment_button
     * @private
     * @return {void}
     */
    _show() {
        if (!this.paymentButton.dataset.isPaypal) {
            super._show();
        }
    },

});
