import { _t } from '@web/core/l10n/translation';
import PaymentForm from '@payment/js/payment_form';

PaymentForm.include({

    /**
     * @override
     */
    async start() {
        this.submitButtons = document.querySelectorAll('[adapt-label-for-cod="True"]');
        this.submitButton = this.submitButtons[0];
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
         let label = this.submitButtonDefaultLabel;
         if (radio.dataset.paymentMethodCode === 'cash_on_delivery') {
             label = _t("Place order");
         }
         this.submitButtons.forEach((btn) => btn.textContent = label);
         return await this._super(...arguments);
     }

});
