import { _t } from '@web/core/l10n/translation';
import PaymentForm from '@payment/js/payment_form';

PaymentForm.include({

     /**
     * Override of `payment`.
     *
     * @private
     * @param {HTMLInputElement} radio - The radio button linked to the payment option.
     * @return {void}
     */
     async _expandInlineForm(radio) {
         const submitButton = document.querySelector('[name="o_payment_submit_button"]');
         if (radio.dataset.paymentMethodCode === 'cash_on_delivery') {
             submitButton.textContent = _t("Place order");
         }
         else {
             submitButton.textContent = _t("Pay Now");
         }
         return await this._super(...arguments);
     }

});
