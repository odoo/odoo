/** @odoo-module **/

import PaymentForm from '@payment/js/payment_form';

PaymentForm.include({

     /**
      * Create an event listener for the payment button located outside the payment form.
      * @override
     */
     async start() {
         const submitButton = document.querySelector('[name="o_payment_submit_button"]');
         submitButton.addEventListener('click', ev => this._submitForm(ev));
         return await this._super(...arguments);
     }

});
