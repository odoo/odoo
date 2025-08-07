import PaymentForm from '@payment/js/payment_form';

PaymentForm.include({

    /**
     * Configure 'pay_on_site' as a pay-later method.
     *
     * @override
     */
    _isPayLaterMethod(paymentMethodCode) {
        return paymentMethodCode === 'pay_on_site' || this._super(...arguments);
    }

});
