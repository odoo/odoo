/** @odoo-module **/
import publicWidget from 'web.public.widget';
import 'website_sale_delivery.checkout';

publicWidget.registry.websiteSaleDelivery.include({
    start: function () {
        this.paymentOptions = $(".o_payment_option_card").find('input[type=radio]');
        return this._super.apply(this, arguments);
    },


    /**
     * @private
     * @param {HTMLElement|JQuery} element The element to lock
     * @param {boolean} lockState to lock or not the element
     * Greys out/remove grey of an html/jquery element
     */
    _setElementLock(element, lockState=true){
        if(lockState) $(element).parent().parent().hide();
        else $(element).parent().parent().show();
    },

    /**
     * @private
     * @param {Event} ev : The html event triggered by clicking a delivery carrier
     * @returns 
     */
    _onCarrierClick: function(ev){
        const result = this._super(...arguments);
        const carrierId = parseInt($(ev.currentTarget).find('input').val());

        for(let option of this.paymentOptions){
            const jOption = $(option);

            this._setElementLock(jOption);

            let carriers = jOption.data('carriers');
            if(carriers != null && carriers.length > 0){
                if(carriers.includes(carrierId)) this._setElementLock(jOption, false);
            }else{
                this._setElementLock(jOption, false);
            }
        }

        return result;
    },
});
