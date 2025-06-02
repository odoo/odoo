import { _t } from '@web/core/l10n/translation';
import { patch } from '@web/core/utils/patch';
import { patchDynamicContent } from '@web/public/utils';

import { PaymentForm } from '@payment/interactions/payment_form';

patch(PaymentForm.prototype, {
    setup() {
        super.setup();
        patchDynamicContent(this.dynamicContent, {
            'input[name="o_donation_amount"]': {
                't-on-change': this.updateAmount.bind(this),
                't-on-focus': this.updateAmount.bind(this),
            },
            'input[name="amount"]': { 't-on-focus': this.updateAmount.bind(this) },
        });
    },

    // #=== EVENT HANDLERS ===#

    /**
     * Update the amount in the payment context with the user input.
     *
     * @param {Event} ev
     * @return {void}
     */
    updateAmount(ev) {
        if (ev.target.value >= 0) {
            this.paymentContext.amount = ev.target.value;
            const otherAmountEl = this.el.querySelector("#other_amount");
            if (ev.target.id === "other_amount_value" && otherAmountEl) {
                otherAmountEl.value = ev.target.value;
            }
            if (ev.target.id === "other_amount" || ev.target.id === "other_amount_value") {
                this.el.querySelectorAll('input[name="o_donation_amount"][type="radio"]').forEach(
                    radioEl => radioEl.checked = false
                );
            } else if (ev.target.name === "o_donation_amount" && otherAmountEl) {
                otherAmountEl.checked = false;
            }
        }
    },

    /**
     * Checks constraints on submit:
     * 1. The value must be greater than the minimum value.
     * 2. A radio button must be checked, if the custom amount is selected.
     * 3. The custom input must have a value.
     *
     * @override method from payment.payment_form
     * @param {Event} ev
     */
    async submitForm(ev) {
        ev.stopPropagation();
        ev.preventDefault();

        const donationAmountInputEl = this.el.querySelector("#other_amount_value");
        const otherAmountRadioEl = this.el.querySelector("#other_amount");
        const considerAmountInput = otherAmountRadioEl ? otherAmountRadioEl.checked : true;
        if (
            donationAmountInputEl &&
            considerAmountInput &&
            (!donationAmountInputEl.value || parseFloat(donationAmountInputEl.value) <= 0)
        ) {
            // If the warning message is already displayed, we don't need to display it again.
            if (this.el.querySelector("#warning_min_message_id").classList.contains("d-none")) {
                this.el.querySelector("#warning_message_id").classList.remove("d-none");
            }
            return donationAmountInputEl.focus();
        }

        await super.submitForm(...arguments);
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
            const mandatoryFields = {
                partner_name: _t("Name"),
                partner_email: _t("Email"),
                partner_country_id: _t("Country"),
            };
            const donationFormEl = document.querySelector("#o_donation_field_form");

            // This code is added here because setting a custom field as
            // required in the form does not work. So, we are manually checking
            // if the field is mandatory.
            donationFormEl
                .querySelectorAll(".s_website_form_required .s_website_form_label")
                .forEach((fieldEl) => {
                    mandatoryFields[fieldEl.getAttribute("for")] = fieldEl.textContent.trim();
                });

            let firstInvalidFieldEl;
            for (const id in mandatoryFields) {
                const fieldEl = donationFormEl.querySelector(
                    `.s_website_form_required .s_website_form_input[id^=${id}], .s_website_form_model_required .s_website_form_input#${id}`
                );
                let isInvalid;
                if (fieldEl.type === "radio" || fieldEl.type === "checkbox") {
                    const checkedEl = donationFormEl.querySelector(
                        `.s_website_form_input[id^=${id}]:checked`
                    );
                    isInvalid = !checkedEl || !checkedEl.value.trim();
                } else {
                    isInvalid =
                        !fieldEl.value.trim() || (id === "email" && !fieldEl.checkValidity());
                }
                fieldEl.classList.toggle("is-invalid", isInvalid);
                if (isInvalid && !firstInvalidFieldEl) {
                    firstInvalidFieldEl = fieldEl;
                }
            }
            if (firstInvalidFieldEl) {
                firstInvalidFieldEl.focus();
                this._enableButton();
                return;
            }

            // This prevents unnecessary toaster notifications on payment failure by catching the
            // Promise.reject as we are already displaying error popup.
            await super._initiatePaymentFlow(...arguments).catch((error) => {
                console.log(error.data.message);
            });
        } else {
            await super._initiatePaymentFlow(...arguments);
        }
    },

    /**
     * Add params used by the donation snippet for the RPC to the transaction route.
     *
     * @override method from @payment/js/payment_form
     * @private
     * @return {object} The extended transaction route params.
     */
    _prepareTransactionRouteParams() {
        const transactionRouteParams = super._prepareTransactionRouteParams(...arguments);

        const getFormData = (formSelector) => {
            const formEl = document.querySelector(formSelector);
            if (!formEl) {
                return {};
            }
            const formData = new FormData(formEl);
            const partnerDetails = {};
            formData.forEach((value, key) => {
                // Retrieve all form elements that share the same name attribute
                // This is necessary for handling cases where multiple inputs
                // exist for a single key (e.g., checkbox groups).
                const fieldEls = formEl.querySelectorAll(`[name="${CSS.escape(key)}"]`);
                const fieldEl = [...fieldEls].find((el) => el.value == value);

                const fieldWrapperEl = fieldEl.closest(".s_website_form_field");
                const labelText = fieldWrapperEl
                    .querySelector(".s_website_form_label_content")
                    ?.innerText.trim();
                // Check whether the field belongs to a required model wrapper.
                // If it does, we need to use the element ID as the key to match
                // the field name with the transaction field. Otherwise, we can
                // use the form field name as the key.
                const modelRequiredEl = fieldEl.closest(".s_website_form_model_required");
                const targetKey = modelRequiredEl ? fieldEl.id : labelText || key;

                if (
                    !modelRequiredEl &&
                    !fieldWrapperEl.classList.contains("s_website_form_custom")
                ) {
                    // Since the form uses a separate model, the existing fields
                    // don’t match the element IDs. To handle this, we need to
                    // check whether the field is a select or a checkbox so we
                    // can retrieve the correct value to display in the logs.
                    if (fieldEl.tagName === "SELECT") {
                        value = fieldEl.options[fieldEl.selectedIndex]?.text.trim();
                    } else if (
                        ["checkbox", "radio"].includes(fieldEl.type) &&
                        fieldEls.length > 1
                    ) {
                        value = formEl
                            .querySelector(`label[for="${fieldEl.id}"]`)
                            ?.innerText.trim();
                    }
                }
                partnerDetails[targetKey] = partnerDetails[targetKey]
                    ? [].concat(partnerDetails[targetKey], value)
                    : value;
            });
            return partnerDetails;
        };
        const partnerDetails = getFormData("#o_donation_field_form");

        return document.querySelector('.o_donation_payment_form')
            ? {
            ...transactionRouteParams,
            partner_id: parseInt(this.paymentContext['partnerId']),
            currency_id: this.paymentContext['currencyId']
                    ? parseInt(this.paymentContext['currencyId']) : null,
            reference_prefix:this.paymentContext['referencePrefix']?.toString(),
            partner_details: partnerDetails,
            donation_comment: this.el.querySelector('#donation_comment').value,
            donation_recipient_email: this.el.querySelector(
                'input[name="donation_recipient_email"]'
            ).value,
        } : transactionRouteParams;
    },

});
