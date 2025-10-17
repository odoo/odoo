import { patch } from '@web/core/utils/patch';
import { url } from "@web/core/utils/urls";

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
        submitButtons.forEach(submitButton => {
            //Buttons that are inside the payment form are ignored as they are already handled by
            // the payment form.
            if (!this.el.contains(submitButton)) { // The button is outside the payment form.
                submitButton.addEventListener('click', boundSubmitForm);
                this.registerCleanup(
                    () => submitButton.removeEventListener('click', boundSubmitForm)
                );
            }
        });
    },

    start() {
        // Display the payment error message if present in the URL.
        const params = new URLSearchParams(window.location.search);
        const errorMsg = params.get("error_msg");
        if (errorMsg) {
            // Clean the URL from the error message.
            params.delete("error_msg");
            history.replaceState(  // Avoid redirecting.
                null, "", url(window.location.pathname, Object.fromEntries(params))
            );
            this.services.notification.add(errorMsg, { type: "danger", sticky: true });
        }
    }
});
