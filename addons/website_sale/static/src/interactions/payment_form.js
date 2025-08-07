import { patch } from '@web/core/utils/patch';

import { PaymentForm } from '@payment/interactions/payment_form';

patch(PaymentForm.prototype, {

     /**
      * Create an event listener for the payment submit buttons located outside the payment form.
      *
      * Buttons that are inside the payment form are ignored as they are already handled by the
      * payment form.
      *
      * @override
     */
     setup() {
         super.setup();
         const submitButtons = document.querySelectorAll('button[name="o_payment_submit_button"]');
         submitButtons.forEach(submitButton => {
             if (!this.el.contains(submitButton)) {  // The button is outside the payment form.
                 submitButton.addEventListener('click', ev => this.submitForm(ev));
             }
         });
     }

});
