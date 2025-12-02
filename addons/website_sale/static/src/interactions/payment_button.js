import { patch } from '@web/core/utils/patch';
import { PaymentButton } from '@payment/interactions/payment_button';

patch(PaymentButton.prototype, {

    /**
     * Verify that the payment button is ready to be enabled.
     *
     * The conditions are that:
     * - a delivery carrier is selected and ready (the price is computed) if deliveries are enabled;
     * - the "Terms and Conditions" checkbox is ticked if it is present.
     *
     * @override method from @payment/interactions/payment_button
     * @return {boolean}
     */
    _canSubmit() {
        return super._canSubmit() && this._isTcCheckboxReady();
    },

    /**
     * Check if the "Terms and Conditions" checkbox is ticked, if present.
     *
     * @private
     * @return {boolean}
     */
    _isTcCheckboxReady() {
        // Find the one T&C checkbox that is not hidden, either the desktop or the mobile one.
        const checkboxes = document.querySelectorAll('#website_sale_tc_checkbox');
        const visibleCheckbox = Array.from(checkboxes).find(el => el.offsetParent !== null);

        if (!visibleCheckbox) { // The checkbox is not present.
            return true; // Ignore the check.
        }

        return visibleCheckbox.checked;
    },

});
