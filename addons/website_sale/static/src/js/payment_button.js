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
        return this._super(...arguments) && this._isCarrierReady() && this._isTCCheckboxReady();
    },

    /**
     * Check if the delivery carrier is selected and if its price is computed.
     *
     * @private
     * @return {boolean}
     */
    _isCarrierReady() {
        const carriers = document.querySelectorAll('.o_delivery_carrier_select');
        if (carriers.length === 0) { // No carrier is available.
            return true; // Ignore the check.
        }

        const checkedCarriers = document.querySelectorAll('input[name="delivery_type"]:checked');
        if (checkedCarriers.length === 0) { // No carrier is selected.
            return false; // Nothing else to check.
        }
        const carriersContainer = checkedCarriers[0].closest('.o_delivery_carrier_select');
        if (carriersContainer.querySelector('.o_wsale_delivery_carrier_error')) {
            // Rate shipment error.
            return false;
        }
        const isPickUpPointRequired = carriersContainer.querySelector('.o_show_pickup_locations');
        if (isPickUpPointRequired) {
            const address = carriersContainer.querySelector(
                '.o_order_location_address'
            ).innerText;
            const isPickUp = carriersContainer.lastChild.previousSibling.children;
            if (
                isPickUp.length > 1 && (address === '' || isPickUp[0].classList.contains('d-none'))
            ) { // A pickup point is required but not selected
                return false;
            }
        }

        return true;
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
