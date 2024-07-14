/** @odoo-module **/

import paymentButton from '@payment/js/payment_button';

paymentButton.include({

    /**
     * Verify that the payment button is ready to be enabled.
     *
     * The condition is that:
     * - The warning ups is hidden.
     *
     * @override from @payment/js/payment_button
     * @return {boolean}
     */
    _canSubmit() {
        return this._super(...arguments) && !document.querySelector('.ups-warning:not(.d-none)');
    }

});
