/** @odoo-module **/

import paymentButton from '@payment/js/payment_button';

paymentButton.include({

    /**
     * Hide the disabled PayPal buttons and show the enabled ones.
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
     * @override method from @payment/js/payment_button
     * @private
     * @return {void}
     */
    _disable() {
        if (!this.paymentButton.dataset.isPaypal) {
            this._super();
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
