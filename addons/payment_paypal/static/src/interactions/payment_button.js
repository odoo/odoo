import { patch } from '@web/core/utils/patch';
import { PaymentButton } from '@payment/interactions/payment_button';

patch(PaymentButton.prototype, {

    /**
     * Hide the disabled PayPal buttons and show the enabled ones.
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

        const paypalButtons = document.querySelectorAll(
            '[id^="o_paypal_disabled_button"], [id^="o_paypal_enabled_button"]'
        );
        paypalButtons.forEach(button => {
            const action = button.id.startsWith('o_paypal_disabled_button') ? 'add' : 'remove';
            button.classList[action]('d-none');
        });
    },

    /**
     * Hide the enabled PayPal buttons and show the disabled ones.
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

        const paypalButtons = document.querySelectorAll(
            '[id^="o_paypal_disabled_button"], [id^="o_paypal_enabled_button"]'
        );
        paypalButtons.forEach(button => {
            const action = button.id.startsWith('o_paypal_enabled_button') ? 'add' : 'remove';
            button.classList[action]('d-none');
        });
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
