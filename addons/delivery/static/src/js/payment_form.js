import { _t } from '@web/core/l10n/translation';
import PaymentForm from '@payment/js/payment_form';

PaymentForm.include({

    /**
     * @override
     */
    async start() {
        this.submitButton = document.querySelector('[adapt-label-for-cod="True"]');
        this.submitButtonDefaultLabel = this.submitButton.textContent;
        await this._super(...arguments);
    },


     /**
     * Override of `payment`.
     *
     * @private
     * @param {HTMLInputElement} radio - The radio button linked to the payment option.
     * @return {void}
     */
     async _expandInlineForm(radio) {
         if (radio.dataset.paymentMethodCode === 'cash_on_delivery') {
             this.submitButton.textContent = _t("Place order");
         }
         else {
             this.submitButton.textContent = this.submitButtonDefaultLabel;
         }
         return await this._super(...arguments);
     }

});
