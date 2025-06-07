/** @odoo-module **/

import paymentButton from '@payment/js/payment_button';

paymentButton.include({

    /**
     * Verify that the payment button is ready to be enabled.
     *
     * The conditions are that:
     * - a delivery carrier is selected and ready (the price is computed) if deliveries are enabled;
     * - the "Terms and Conditions" checkbox is ticked if it is present.
     *
     * @override from @payment/js/payment_button
     * @return {boolean}
     */
    _canSubmit() {
        return this._super(...arguments) && this._isTCCheckboxReady();
    },

    /**
     * Check if the "Terms and Conditions" checkbox is ticked, if present.
     *
     * @private
     * @return {boolean}
     */
    _isTCCheckboxReady() {
        const checkbox = document.querySelector('#website_sale_tc_checkbox');
        if (!checkbox) { // The checkbox is not present.
            return true;  // Ignore the check.
        }

        return checkbox.checked;
    },

});
