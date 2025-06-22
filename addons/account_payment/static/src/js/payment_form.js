import PaymentForm from "@payment/js/payment_form";

PaymentForm.include({

    /**
     * @override
     */
    async start() {
        await this._super(...arguments);
        this._onChangePaymentTabs();
    },

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

        /**
     * Prepare the params for the RPC to the transaction route.
     *
     * @override method from payment.payment_form
     * @private
     * @return {object} The transaction route params.
     */
        _prepareTransactionRouteParams() {
            const transactionRouteParams =  this._super(...arguments);
            transactionRouteParams.payment_reference = this.paymentContext.paymentReference;
            return transactionRouteParams;
        },

    /**
     * Handles payment tab changes (installment or full amount).
     *
     * This method listens for the `shown.bs.tab` event on payment tab buttons.
     * When the user switches tabs, it updates the URL parameters `mode` and
     * `render_change`, then reloads the page. This forces the backend to
     * re-render the payment form with updated data, including the corresponding
     * amount and available payment providers.
     *
     * Added URL parameters:
     * - mode: either 'installment' or 'full', depending on the selected tab.
     * - render_change: 'true', indicating that the change should trigger a re-render.
     */
    _onChangePaymentTabs() {
        $('.o_btn_payment_tab').on('shown.bs.tab', function (event) {
            const activatedTab = event.target.id;
            let mode = (activatedTab === 'o_payment_installments_tab')
                ? 'installment'
                : (activatedTab === 'o_payment_full_tab' ? 'full' : false);

            if (mode) {
                const url = new URL(window.location.href);
                url.searchParams.set('mode', mode);
                url.searchParams.set('render_change', 'true');

                window.location.href = url.toString();
            }
        });
    }
});
