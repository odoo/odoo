/** @odoo-module **/

import { _t } from '@web/core/l10n/translation';

import PaymentForm from '@payment/js/payment_form';

PaymentForm.include({
    events: Object.assign({}, PaymentForm.prototype.events || {}, {
        'change input[name="o_donation_amount"]': '_updateAmount',
        'focus input[name="amount"]': '_updateAmount',
        'focus input[name="o_donation_amount"]': '_updateAmount',
    }),


    // #=== EVENT HANDLERS ===#

    /**
     * Update the amount in the payment context with the user input.
     *
     * @private
     * @param {Event} ev
     * @return {void}
     */
    _updateAmount(ev) {
        if (ev.target.value >= 0) {
            this.paymentContext.amount = ev.target.value;
            const otherAmountEl = this.el.querySelector("#other_amount");
            if (ev.target.id === "other_amount_value" && otherAmountEl) {
                otherAmountEl.value = ev.target.value;
            }
            if (ev.target.id === "other_amount" || ev.target.id === "other_amount_value") {
                this.el.querySelectorAll('input[name="o_donation_amount"][type="radio"]').forEach((radioEl) => {
                    radioEl.checked = false;
                });
            } else if (ev.target.name === "o_donation_amount" && otherAmountEl) {
                otherAmountEl.checked = false;
            }
        }
    },

    // #=== PAYMENT FLOW ===#

    /**
     * Perform some validations for donations before processing the payment flow.
     *
     * @override method from @payment/js/payment_form
     * @private
     * @param {string} providerCode - The code of the selected payment option's provider.
     * @param {number} paymentOptionId - The id of the selected payment option.
     * @param {string} paymentMethodCode - The code of the selected payment method, if any.
     * @param {string} flow - The payment flow of the selected payment option.
     * @return {void}
     */
    async _initiatePaymentFlow(providerCode, paymentOptionId, paymentMethodCode, flow) {
        if (document.querySelector('.o_donation_payment_form')) {
            const errorFields = {};
            if (!this.el.querySelector('input[name="email"]').checkValidity()) {
                errorFields['email'] = _t("Email is invalid");
            }
            const mandatoryFields = {
                'name': _t('Name'),
                'email': _t('Email'),
                'country_id': _t('Country'),
            };
            for (const id in mandatoryFields) {
                const fieldEl = this.el.querySelector(`input[name="${id}"],select[name="${id}"]`);
                fieldEl.classList.remove('is-invalid');
                Popover.getOrCreateInstance(fieldEl)?.dispose();
                if (!fieldEl.value.trim()) {
                    errorFields[id] = _t("Field '%s' is mandatory", mandatoryFields[id]);
                }
            }
            if (Object.keys(errorFields).length) {
                for (const id in errorFields) {
                    const fieldEl = this.el.querySelector(
                        `input[name="${id}"],select[name="${id}"]`
                    );
                    fieldEl.classList.add('is-invalid');
                    Popover.getOrCreateInstance(fieldEl, {
                        content: errorFields[id],
                        placement: 'top',
                        trigger: 'hover',
                    });
                }
                this._displayErrorDialog(
                    _t("Payment processing failed"),
                    _t("Some information is missing to process your payment.")
                );
                this._enableButton();
                return;
            }
        }
        await this._super(...arguments);
    },

    /**
     * Add params used by the donation snippet for the RPC to the transaction route.
     *
     * @override method from @payment/js/payment_form
     * @private
     * @return {object} The extended transaction route params.
     */
    _prepareTransactionRouteParams() {
        const transactionRouteParams = this._super(...arguments);
        return document.querySelector('.o_donation_payment_form')
            ? {
            ...transactionRouteParams,
            partner_id: parseInt(this.paymentContext['partnerId']),
            currency_id: this.paymentContext['currencyId']
                    ? parseInt(this.paymentContext['currencyId']) : null,
            reference_prefix:this.paymentContext['referencePrefix']?.toString(),
            partner_details: {
                name: this.el.querySelector('input[name="name"]').value,
                email: this.el.querySelector('input[name="email"]').value,
                country_id: this.el.querySelector('select[name="country_id"]').value,
            },
            donation_comment: this.el.querySelector('#donation_comment').value,
            donation_recipient_email: this.el.querySelector(
                'input[name="donation_recipient_email"]'
            ).value,
        } : transactionRouteParams;
    },

});
