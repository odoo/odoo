import { _t } from '@web/core/l10n/translation';
import { patch } from '@web/core/utils/patch';

import { PaymentForm } from '@payment/interactions/payment_form';

patch(PaymentForm.prototype, {

    /**
     * Determine the label for the submit button based on the selected payment method.
     *
     * @override
     */
    _getSubmitButtonLabel(paymentMethodCode) {
        if (paymentMethodCode === 'cash_on_delivery') {
            return _t('Confirm');
        }
        return  super._getSubmitButtonLabel(paymentMethodCode);
    }

});
