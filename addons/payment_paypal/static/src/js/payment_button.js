/** @odoo-module **/

import paymentButton from '@payment/js/payment_button';

paymentButton.include({

    /**
     * Hide the disabled PayPal button and show the enabled one.
     *
     * @override method from @payment/js/payment_button
     * @private
     * @return {void}
     */
    _setEnabled() {
        if (!this.paymentButton.dataset.isPaypal) {
            this._super();
            return;
        }

        document.getElementById('o_paypal_disabled_button').classList.add('d-none');
        document.getElementById('o_paypal_enabled_button').classList.remove('d-none');
    },

    /**
     * Hide the enabled PayPal button and show the disabled one.
     *
     * @override method from @payment/js/payment_button
     * @private
     * @return {void}
     */
    _disable() {
        if (!this.paymentButton.dataset.isPaypal) {
            this._super();
            return;
        }

        document.getElementById('o_paypal_disabled_button').classList.remove('d-none');
        document.getElementById('o_paypal_enabled_button').classList.add('d-none');
    },

    /**
     * Disable the generic behavior that would hide the Paypal button container.
     *
     * @override method from @payment/js/payment_button
     * @private
     * @return {void}
     */
    _hide() {
        if (!this.paymentButton.dataset.isPaypal) {
            this._super();
        }
    },

    /**
     * Disable the generic behavior that would show the Paypal button container.
     *
     * @override method from @payment/js/payment_button
     * @private
     * @return {void}
     */
    _show() {
        if (!this.paymentButton.dataset.isPaypal) {
            this._super();
        }
    },

});
