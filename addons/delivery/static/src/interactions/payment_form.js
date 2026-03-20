import { patch } from '@web/core/utils/patch';

import { PaymentForm } from '@payment/interactions/payment_form';

patch(PaymentForm.prototype, {

    /**
     * Configure 'cash_on_delivery' as a pay later method.
     *
     * @override
     */
    _isPayLaterPaymentMethod(paymentMethodCode) {
        return (
            paymentMethodCode === 'cash_on_delivery'
            || super._isPayLaterPaymentMethod(...arguments)
        );
    }

});
