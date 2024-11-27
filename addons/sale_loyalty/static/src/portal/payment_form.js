import PaymentForm from '@payment/js/payment_form';

PaymentForm.include({
    _prepareTransactionRouteParams(){
        let transactionRouteParams = this._super.apply(this, arguments);
        if(this.el.dataset.landingRoute === '/topup/pay/confirm/'){
            Object.assign(transactionRouteParams, {
                'currency_id': this.paymentContext['currencyId']
                    ? parseInt(this.paymentContext['currencyId']) : null,
            });
        }
        return transactionRouteParams;
    }
})