/** @odoo-module **/

    import paymentForm from '@payment/js/payment_form';


    const xenditMixin = {

        _initiatePaymentFlow(provider, paymentOptionId, paymentMethodCode, flow) {
            if (provider !== 'xendit' || flow === 'token') {
                this._super(...arguments); // Tokens are handled by the generic flow
                return;
            }
            // The `onError` event handler is not used to validate inputs anymore since v5.0.0.
            this.rpc(
                this.paymentContext['transactionRoute'],
                this._prepareTransactionRouteParams(),
            ).then(processingValues => {
                return this.rpc(
                    '/payment/xendit/payment_methods', {
                        "provider_id": processingValues.provider_id,
                        "reference": processingValues.reference,
                        "amount": processingValues.amount,
                        "currency_id": processingValues.currency_id,
                        "partner_id": processingValues.partner_id,
                    }
                )
            }).then(paymentResponse => {
                const $redirectForm = $('<form></form>').attr('id', 'o_payment_redirect_form')
                $redirectForm[0].setAttribute('target', '_top');
                $redirectForm[0].setAttribute('action', paymentResponse.url);
                $(document.getElementsByTagName('body')[0]).append($redirectForm);

                $redirectForm.submit()
            }).guardedCatch((error) =>{
                error.event.preventDefault();
                // this._displayErrorDialog(_t("Payment processing failed"), error.message.data.message);
                this._enableButton();
            })
        },
    }

    paymentForm.include(xenditMixin)
