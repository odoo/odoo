import { registry } from '@web/core/registry';
import { Interaction } from '@web/public/interaction';
import { useListener } from "@odoo/owl";

export class PaymentButton extends Interaction {
    static selector = '[name="o_payment_submit_button"]';

    setup() {
        this.paymentButton = this.el;
        this.iconClass = this.paymentButton.dataset.iconClass;
        this._enable();
        useListener(this.env.bus, 'enablePaymentButton', this._enable.bind(this));
        useListener(this.env.bus, 'disablePaymentButton', this._disable.bind(this));
        useListener(this.env.bus, 'hidePaymentButton', this._hide.bind(this));
        useListener(this.env.bus, 'showPaymentButton', this._show.bind(this));
    }

    /**
     * Check if the payment button can be enabled and do it if so.
     *
     * @private
     * @return {void}
     */
    _enable() {
        if (this._canSubmit()) {
            this._setEnabled();
        }
    }

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
    }

    /**
     * Enable the payment button.
     *
     * @private
     * @return {void}
     */
    _setEnabled() {
        this.paymentButton.disabled = false;
    }

    /**
     * Disable the payment button.
     *
     * @private
     * @return {void}
     */
    _disable() {
        this.paymentButton.disabled = true;
    }

    /**
     * Hide the payment button.
     *
     * @private
     * @return {void}
     */
    _hide() {
        this.paymentButton.classList.add('d-none');
    }

    /**
     * Show the payment button.
     *
     * @private
     * @return {void}
     */
    _show() {
        this.paymentButton.classList.remove('d-none');
    }
}

registry.category('public.interactions').add('payment.payment_button', PaymentButton);
