import { patch } from '@web/core/utils/patch';

import { PaymentForm } from '@payment/interactions/payment_form';

patch(PaymentForm.prototype, {

    /**
     * Configure 'pay_on_site' as a pay later method.
     *
     * @override
     */
    _isPayLaterPaymentMethod(paymentMethodCode) {
        return paymentMethodCode === 'pay_on_site' || super._isPayLaterPaymentMethod(...arguments);
    }

});
