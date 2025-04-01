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
            // Update paymentContext of second form as amount is mentioned
            // on second's dataset.
            document.querySelector(".o_payment_form").dataset.amount = ev.target.value;
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
            if (!document.querySelector('input[name="email"]').checkValidity()) {
                errorFields['email'] = _t("Email is invalid");
            }
            const mandatoryFields = {
                'name': _t('Name'),
                'email': _t('Email'),
                'country_id': _t('Country'),
            };

            // This code is added here because setting a custom field as required
            // in the form does not work. So, we are manually checking if the field is mandatory.
            document.querySelectorAll('.s_website_form_required').forEach((field) => {
                const inputEl = field.querySelector('input, select');
                if (inputEl && inputEl.name) {
                    mandatoryFields[inputEl.name] = field.textContent.trim();
                }
            });

            for (const id in mandatoryFields) {
                const fieldEl = document.querySelector(`input[name="${id}"],select[name="${id}"]`);
                fieldEl.classList.remove('is-invalid');
                Popover.getOrCreateInstance(fieldEl)?.dispose();
                if (!fieldEl.value.trim()) {
                    errorFields[id] = _t("Field '%s' is mandatory", mandatoryFields[id]);
                }
            }
            if (Object.keys(errorFields).length) {
                for (const id in errorFields) {
                    const fieldEl = document.querySelector(
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
        //To update the amount after change it from form.
        //The paymentContext['amount'] is in second form. So, The amount
        //doesn't get updated after we change it through form.
        transactionRouteParams.amount = parseFloat(
            document.querySelector(".o_payment_form").dataset.amount
        );
        const getFormData = (formSelector) => {
            const form = document.querySelector(formSelector);
            if (!form) {
                return {};
            }
            const formData = new FormData(form)
            const partnerDetails = {};
            formData.forEach((value, key) => {
                partnerDetails[key] = value;
            });
            return partnerDetails;
        };

        const partnerDetails = getFormData(".o_payment_field_form");
        return document.querySelector('.o_donation_payment_form')
            ? {
            ...transactionRouteParams,
            partner_id: parseInt(this.paymentContext['partnerId']),
            currency_id: this.paymentContext['currencyId']
                    ? parseInt(this.paymentContext['currencyId']) : null,
            reference_prefix:this.paymentContext['referencePrefix']?.toString(),
            partner_details: partnerDetails,
            donation_comment: document.querySelector('#donation_comment').value,
            donation_recipient_email: document.querySelector(
                'input[name="donation_recipient_email"]'
            ).value,
        } : transactionRouteParams;
    },

});
