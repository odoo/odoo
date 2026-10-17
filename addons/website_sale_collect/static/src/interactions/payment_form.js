import { patch } from '@web/core/utils/patch';
import { _t } from '@web/core/l10n/translation';

import { PaymentForm } from '@payment/interactions/payment_form';

patch(PaymentForm.prototype, {

    setup() {
        super.setup();

        this.deliveryAddressTitle = this.el.querySelector('[name="delivery_address_title"]');
        if (this.deliveryAddressTitle) {
            this.deliveryTitle = this.deliveryAddressTitle.textContent;
            this.useDeliveryAsBillingLabel = this.el.querySelector(
                '[name="use_delivery_as_billing_text"]'
            );
            this.useDeliveryAsBillingLabelText = this.useDeliveryAsBillingLabel.textContent;
            this.inStoreTitle = _t('Contact Details');
            this.useDeliveryAsBillingLabelInStoreText = _t('Same as contact details');
            this._adaptDeliveryTitles();
        }
    },

    /**
     * Configure 'pay_on_site' as a pay later method.
     *
     * @override
     */
    _isPayLaterPaymentMethod(paymentMethodCode) {
        return paymentMethodCode === 'pay_on_site' || super._isPayLaterPaymentMethod(...arguments);
    },

    /**
     * Change the delivery address title and the 'use delivery as billing' label depending on the
     * selected delivery method.
     *
     * @private
     * @return {void}
     */
    _adaptDeliveryTitles() {
        const checkedRadio = this._getSelectedDeliveryRadio();
        if (!checkedRadio || !this.deliveryAddressTitle || !this.useDeliveryAsBillingLabel) {
            return;
        }
        if (checkedRadio.dataset.deliveryType === 'in_store') {
            this.deliveryAddressTitle.textContent = this.inStoreTitle;
            this.useDeliveryAsBillingLabel.textContent = this.useDeliveryAsBillingLabelInStoreText;
        } else {
            this.deliveryAddressTitle.textContent = this.deliveryTitle;
            this.useDeliveryAsBillingLabel.textContent = this.useDeliveryAsBillingLabelText;
        }
    },

});
