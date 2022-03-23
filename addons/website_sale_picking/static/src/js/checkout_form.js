/** @odoo-module */

import publicWidget from 'web.public.widget';
import 'website_sale_delivery.checkout';

publicWidget.registry.websiteSaleDelivery.include({
    start: function () {
        this.paymentOptions = document.querySelectorAll('.o_payment_option_card input[type=radio]');
        return this._super.apply(this, ...arguments);
    },

    /**
     * Hides or shows a payment option card.
     * @param node the input element of the payment option card
     * @param enabled whether to show or hide the card
     * @private
     */
    _setEnablePaymentOption(node, enabled=false){
        if(enabled){
            node.parentNode.parentNode.classList.remove('d-none');
            try{
                $(node).click();
            }catch (_){ // During a tour, if the button is clicked very quickly, it seems the code handling the payment click is not yet ready ?
                node.checked = true;
            }
        }
        else{
            node.parentNode.parentNode.classList.add('d-none');
            node.checked = false;
        }
    },

    /**
     * Checks all payment options and hides them if it is an onsite payment option and the delivery is not onsite.
     * @param {Event} ev the triggered document event
     * @private
     */
    _onCarrierClick: function (ev) {
        this._super(...arguments);
        const input = ev.currentTarget.querySelector('input');
        for(let option of this.paymentOptions) {
            if (option.dataset.isOnsite && input.dataset.deliveryType !== 'onsite') {
                this._setEnablePaymentOption(option, false);
            }else{
                this._setEnablePaymentOption(option, true);
            }
        }
    }
});
