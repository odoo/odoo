import { patch } from '@web/core/utils/patch';
import { rpc } from '@web/core/network/rpc';
import { url, redirect } from "@web/core/utils/urls";

import { PaymentForm } from '@payment/interactions/payment_form';

patch(PaymentForm.prototype, {

    /**
     * @override
     */
    setup() {
        super.setup();
        const submitButtons = document.querySelectorAll('button[name="o_payment_submit_button"]');
        const boundSubmitForm = this.submitForm.bind(this);
        // Create an event listener for the payment submit buttons located outside the payment form.
        // The payment form already handles those that are located inside it.
        submitButtons.forEach(submitButton => {
            if (!this.el.contains(submitButton)) { // The button is outside the payment form.
                submitButton.addEventListener('click', boundSubmitForm);
                this.registerCleanup(
                    () => submitButton.removeEventListener('click', boundSubmitForm)
                );
            }
        });
    },

    start() {
        // Display the payment status message if present in the URL
        const params = new URLSearchParams(window.location.search);
        const paymentMsg = params.get("payment_msg");
        if (paymentMsg) {
            const paymentMsgType = params.get("payment_msg_type") || "danger";
            // Clean the URL from the payment status message
            params.delete("payment_msg");
            params.delete("payment_msg_type");
            history.replaceState( // Avoid redirecting
                null, "", url(window.location.pathname, Object.fromEntries(params))
            );
            this.services.notification.add(paymentMsg, { type: paymentMsgType, sticky: true });
        }
    },

    /**
     * Save the billing address before initiating the payment flow.
     *
     * @override
     */
    async submitForm(ev) {
        // Prevent the default behavior before awaiting, as it would be too late afterward.
        ev.stopPropagation();
        ev.preventDefault();
        if (!(await this.waitFor(this._saveBillingAddress()))) {
            return;
        }
        await super.submitForm(ev);
    },

    /**
     * Set the billing address on the order.
     *
     * If no invoice is requested, the customer's main address is used as billing address. If "Same
     * as shipping address" is chosen, the delivery address is used as billing address. Otherwise, the billing address is created or updated with the values of the billing address
     * form, if displayed.
     *
     * @private
     * @return {boolean} Whether the payment flow can be initiated.
     */
    async _saveBillingAddress() {
        const useDeliveryAsBillingRadio = document.getElementById('use_delivery_as_billing');
        const setInvoiceAddressInput = document.getElementById('set_invoice_address_input');
        if (setInvoiceAddressInput && !setInvoiceAddressInput.checked) {
            await this.waitFor(rpc('/shop/update_address', {
                address_type: 'billing',
                partner_id: setInvoiceAddressInput.dataset.partnerId,
            }));
            return true;
        }
        if (useDeliveryAsBillingRadio?.checked) {
            await this.waitFor(rpc('/shop/update_address', {
                address_type: 'billing',
                partner_id: useDeliveryAsBillingRadio.dataset.partnerId,
            }));
            return true;
        }
        const billingAddressFormContainer = document.getElementById(
            'billing_address_form_container'
        );
        if (!billingAddressFormContainer || billingAddressFormContainer.offsetParent === null) {
            return true;
        }
        const addressForm = billingAddressFormContainer.querySelector('form[name="address_form"]');
        if (!addressForm.reportValidity()) {
            return false;
        }

        this._disableButton(true);
        let result;
        try {
            result = await this.waitFor(this.services.http.post(
                addressForm.dataset.submitUrl, new FormData(addressForm)
            ));
        } finally {
            // Unblock the UI as the payment flow blocks it again, if it is initiated.
            this._enableButton();
        }
        // Highlight the missing/invalid form values, if any.
        const invalidFields = result.invalid_fields ?? [];
        addressForm.querySelectorAll('.is-invalid').forEach(input => {
            if (!invalidFields.includes(input.name)) {
                input.classList.remove('is-invalid');
            }
        });
        if (invalidFields.length) {
            invalidFields.forEach(fieldName => addressForm[fieldName]?.classList.add('is-invalid'));
            result.messages.forEach(
                message => this.services.notification.add(message, { type: 'danger' })
            );
            return false;
        }
        return true;
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
