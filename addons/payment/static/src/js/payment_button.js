/** @odoo-module **/

import publicWidget from 'web.public.widget';
import core from 'web.core';

publicWidget.registry.PaymentButton = publicWidget.Widget.extend({
    selector: 'button[name="o_payment_submit_button"]',

    async start() {
        await this._super(...arguments);
        this.paymentButton = this.el;
        this.iconClass = this.paymentButton.dataset.iconClass;
        this._enable();
        core.bus.on('enablePaymentButton', this, this._enable);
        core.bus.on('disablePaymentButton', this, this._disable);
    },

    /**
     * Check if the payment button can be enabled and do it if so.
     *
     * The icons are updated to show that the button is ready.
     *
     * @private
     * @return {void}
     */
    _enable() {
        if (this._isReady()) {
            this.paymentButton.disabled = false;
            this.paymentButton.querySelector('i').classList.add(this.iconClass);
            this.paymentButton.querySelector('span.o_loader')?.remove();
        }
    },

    /**
     * Verify that the payment button is ready to be enabled.
     *
     * The condition is that exactly one payment provider's radio must be selected.
     *
     * For a module to support a custom behavior for the payment button, it must override this
     * method and only return true if the result of this method is true and if nothing prevents
     * enabling the submit button for that custom behavior.
     *
     * @private
     * @return {boolean} Whether the payment button can be enabled.
     */
    _isReady() {
        const paymentForm = this.paymentButton.closest('.o_payment_form');
        if (!paymentForm) {  // Neither the checkout form nor the manage form are present.
            return true; // Ignore the check.
        }

        const checkedRadios = paymentForm.querySelectorAll('input[name="o_payment_radio"]:checked');
        return checkedRadios.length === 1;
    },

    /**
     * Disable the payment button.
     *
     * The icons are updated to either show that an action is processing or that the button is
     * not ready, depending on the value of `showLoadingAnimation`.
     *
     * @private
     * @param {boolean} showLoadingAnimation - Whether a spinning loader should be shown.
     * @return {void}
     */
    _disable(showLoadingAnimation = false) {
        this.paymentButton.disabled = true;
        if (showLoadingAnimation) {
            this.paymentButton.querySelector('i').classList.remove(this.iconClass);
            const span = document.createElement('span');
            span.classList.add('o_loader');
            span.innerHTML = '<i class="fa fa-refresh fa-spin"></i>&nbsp;'
            this.paymentButton.prepend(span);
        }
    },

});
export default publicWidget.registry.PaymentButton;
