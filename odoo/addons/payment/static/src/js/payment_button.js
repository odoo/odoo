/** @odoo-module **/

import publicWidget from '@web/legacy/js/public/public_widget';
import { Component } from "@odoo/owl";

publicWidget.registry.PaymentButton = publicWidget.Widget.extend({
    selector: 'button[name="o_payment_submit_button"]',

    async start() {
        await this._super(...arguments);
        this.paymentButton = this.el;
        this.iconClass = this.paymentButton.dataset.iconClass;
        this._enable();
        Component.env.bus.addEventListener('enablePaymentButton', this._enable.bind(this));
        Component.env.bus.addEventListener('disablePaymentButton',this._disable.bind(this));
        Component.env.bus.addEventListener('hidePaymentButton', this._hide.bind(this));
        Component.env.bus.addEventListener('showPaymentButton', this._show.bind(this));
    },

    /**
     * Check if the payment button can be enabled and do it if so.
     *
     * @private
     * @return {void}
     */
    _enable() {
        if (this._canSubmit()) {
            this.paymentButton.disabled = false;
        }
    },

    /**
     * Check whether the payment form can be submitted, i.e. whether exactly one payment option is
     * selected.
     *
     * For a module to add a condition on the submission of the form, it must override this method
     * and return whether both this method's condition and the override method's condition are met.
     *
     * @private
     * @return {boolean} Whether the form can be submitted.
     */
    _canSubmit() {
        const paymentForm = document.querySelector('#o_payment_form');
        if (!paymentForm) {  // Payment form is not present.
            return true; // Ignore the check.
        }
        return document.querySelectorAll('input[name="o_payment_radio"]:checked').length === 1;
    },

    /**
     * Disable the payment button.
     *
     * @private
     * @return {void}
     */
    _disable() {
        this.paymentButton.disabled = true;
    },

    /**
     * Hide the payment button.
     *
     * @private
     * @return {void}
     */
    _hide() {
        this.paymentButton.classList.add('d-none');
    },

    /**
     * Show the payment button.
     *
     * @private
     * @return {void}
     */
    _show() {
        this.paymentButton.classList.remove('d-none');
    },

});
export default publicWidget.registry.PaymentButton;
