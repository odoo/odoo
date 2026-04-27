/** @odoo-module **/

import WebsiteSaleCheckout from '@website_sale/js/checkout'

WebsiteSaleCheckout.include({
    events: Object.assign({}, WebsiteSaleCheckout.prototype.events || {}, {
        'click [name="ups_bill_my_account"]': '_onClickBillMyAccount',
    }),

    async _onClickBillMyAccount(ev) {
        const radio = this._getDeliveryMethodContainer(ev.currentTarget).querySelector(
            'input[type="radio"]'
        );
        // if the delivery method is not selected and delivery rate is successful
        if (!radio.checked && !radio.disabled) {
            radio.checked = true;
            await this._updateDeliveryMethod(radio); // select it
        }
    },

    /**
     * @override
     * @private
     */
     _toggleDeliveryMethodRadio(radio, disable){
         this._super.apply(this, arguments);
         if (radio.dataset.deliveryType !== 'ups') return;
         const carrierContainer = this._getDeliveryMethodContainer(radio);
         const billMyAccountHref = carrierContainer.querySelector('[name="ups_bill_my_account"] a');
         if (!billMyAccountHref) return;
         // Disable bill my account href if radio button is disabled.
         if (disable) {billMyAccountHref.classList.add('disabled');}
         // Enable bill my account href if radio button is enabled.
         else {billMyAccountHref.classList.remove('disabled');}
     }
})
