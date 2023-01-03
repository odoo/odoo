/** @odoo-module **/

import { paymentExpressCheckoutForm } from '@payment/js/express_checkout_form';

paymentExpressCheckoutForm.include({
    /**
     * Return whether the shipping information is required or not
     *
     * @private
     * @override method from payment.express_form
     * @return {Boolean} - Whether the shipping information is required or not
     */
    _isShippingInformationRequired: () => true,
});
