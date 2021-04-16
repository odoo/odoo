/** @odoo-module **/

import {_t} from 'web.core';
import checkoutForm from 'payment.checkout_form';

checkoutForm.include({
    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Perform some validations for donations before performing payment 
     *
     * @override method from payment.payment_form_mixin
     * @private
     * @param {string} provider - The provider of the payment option's acquirer
     * @param {number} paymentOptionId - The id of the payment option handling the transaction
     * @param {string} flow - The online payment flow of the transaction
     * @return {Promise}
     */
    _processPayment: function (provider, paymentOptionId, flow) {
        if ($('.o_donation_payment_form').length) {
            const errorFields = {};
            if (!this.$('input[name="email"]')[0].checkValidity()) {
                errorFields['email'] = _t("Email is invalid");
            }
            const mandatoryFields = {
                'name': _t('Name'),
                'email': _t('Email'),
                'country_id': _t('Country'),
            };
            for (const id in mandatoryFields) {
                const $field = this.$('input[name="' + id + '"],select[name="' + id + '"]');
                $field.removeClass('is-invalid').popover('dispose');
                if (!$field.val().trim()) {
                    errorFields[id] = _.str.sprintf(_t("Field '%s' is mandatory"), mandatoryFields[id]);
                }
            }
            if (Object.keys(errorFields).length) {
                for (const id in errorFields) {
                    const $field = this.$('input[name="' + id + '"],select[name="' + id + '"]');
                    $field.addClass('is-invalid');
                    $field.popover({content: errorFields[id], trigger: 'hover', container: 'body', placement: 'top'});
                    $field.data("bs.popover").config.content = errorFields[id];
                }
                this._displayError(
                    _t("Validation Error"),
                    _t("Some information is missing to process your payment.")
                );
                return Promise.resolve();
            }
        }
        return this._super(...arguments);
    },
    /**
     * Add params used by the donation snippet to the transaction route params.
     *
     * @override method from payment.payment_form_mixin
     * @private
     * @param {string} provider - The provider of the selected payment option's acquirer
     * @param {number} paymentOptionId - The id of the selected payment option
     * @param {string} flow - The online payment flow of the selected payment option
     * @return {object} The extended transaction route params
     */
    _prepareTransactionRouteParams: function (provider, paymentOptionId, flow) {
        const transactionRouteParams = this._super(...arguments);
        return $('.o_donation_payment_form').length ? {
            ...transactionRouteParams,
            'partner_details': {
                'name': this.$('input[name="name"]').val(),
                'email': this.$('input[name="email"]').val(),
                'country_id': this.$('select[name="country_id"]').val(),
            },
            'donation_comment': this.$('#donation_comment').val(),
            'donation_recipient_email': this.$('input[name="donation_recipient_email"]').val(),
        } : transactionRouteParams;
    },
});
