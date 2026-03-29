/** @odoo-module **/
import paymentForm from '@payment/js/payment_form';

paymentForm.include({
    async _prepareInlineForm(providerId, providerCode, paymentOptionId, paymentMethodCode, flow) {
        if (providerCode !== 'bictorys') {
            await this._super(...arguments);
            return;
        }
        // Redirect flow only, do nothing else
        this._setPaymentFlow('redirect');
        console.log('[Bictorys] redirect flow set, no inline form');
    },
});