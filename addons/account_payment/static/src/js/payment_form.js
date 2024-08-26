/** @odoo-module **/

import PaymentForm from "@payment/js/payment_form";

PaymentForm.include({
    /**
     * Set whether we are paying an installment before submitting.
     *
     * @override method from payment.payment_form
     * @private
     * @param {Event} ev
     * @returns {void}
     */
    async _submitForm(ev) {
        ev.stopPropagation();
        ev.preventDefault();

        const paymentDialog = this.el.closest("#pay_with");
        const chosenPaymentDetails = paymentDialog
            ? paymentDialog.querySelector(".o_btn_payment_tab.active")
            : null;
        if (chosenPaymentDetails){
            if (chosenPaymentDetails.id === "o_payment_installments_tab") {
                this.paymentContext.amount = parseFloat(this.paymentContext.invoiceNextAmountToPay);
            } else {
                this.paymentContext.amount = parseFloat(this.paymentContext.invoiceAmountDue);
            }
        }
        await this._super(...arguments);
    },
});
