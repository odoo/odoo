/** @odoo-module **/

import core from 'web.core';
import {_t} from 'web.core';
import checkoutForm from 'payment.checkout_form';
import { memoize } from "@web/core/utils/functions";

checkoutForm.include({
    events: _.extend({}, checkoutForm.prototype.events || {}, {
        'change .o_wpayment_fee_impact': '_onFeeParameterChange',
        'focus .o_wpayment_fee_impact': '_onFeeParameterChange',
    }),

    /**
     * @override
     */
    start: function () {
        core.bus.on('update_shipping_cost', this, this._updateShippingCost);
        this._memoizedGetAcquirerFees = memoize(this._getAcquirerFees.bind(this));
        return this._super.apply(this, arguments);
    },

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

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Update the total amount to be paid.
     *
     * Called upon change of shipping method
     *
     * @private
     * @param {float} amount
     */
     _updateShippingCost: function (amount) {
        this.txContext.amount = amount;
     },
    /**
     * Update the fees associated to each acquirer.
     *
     * Called upon change of any parameter that might impact the fees (marked with
     * .o_wpayment_fee_impact).
     *
     * @private
     * @param {Event} ev
     * @return {undefined}
     */
    _onFeeParameterChange: function (ev) {
        const targetId = ev.target.id;
        if (targetId.indexOf("amount") >= 0) {
            this.txContext.amount = ev.target.value;
            if (targetId === "other_amount_value") {
                //We need to do this because the custom amount is represented by two inputs.
                const otherAmountInputEl = document.querySelector("input[id=\"other_amount\"]");
                if (otherAmountInputEl) {
                    otherAmountInputEl.value = ev.target.value;
                }
            }
        }
        const acquirerIds = [];
        for (const card of this.$('.o_payment_option_card:has(.o_payment_fee)')) {
            const radio = $(card).find('input[name="o_payment_radio"]');
            if (radio.data("paymentOptionType") === 'acquirer') {
                acquirerIds.push(radio.data("paymentOptionId"));
            }
        }
        const countryId = this.$('select[name="country_id"]').val();
        if (acquirerIds && this.txContext.amount) {
            const params = {
                'acquirer_ids': acquirerIds,
                'amount': this.txContext.amount !== undefined
                    ? parseFloat(this.txContext.amount) : null,
                'currency_id': this.txContext.currencyId
                    ? parseInt(this.txContext.currencyId) : null,
                'country_id': countryId,
            }
            const cacheKey = `${params.amount}-${params.currency_id}-${params.country_id}`;

            this._memoizedGetAcquirerFees(cacheKey, params).then(feesPerAcquirer => {
                for (const card of this.$('.o_payment_option_card:has(.o_payment_fee)')) {
                    const radio = $(card).find('input[name="o_payment_radio"]');
                    if (radio.data("paymentOptionType") === 'acquirer') {
                        const acquirerId = radio.data("paymentOptionId");
                        const chunk = $(card).find('.o_payment_fee .oe_currency_value')[0];
                        chunk.innerText = (feesPerAcquirer[acquirerId] || 0).toFixed(2);
                    }
                }
            }).guardedCatch(error => {
                error.event.preventDefault();
                this._displayError(
                    _t("Server Error"),
                    _t("We could not obtain payment fees."),
                    error.message.data.message
                );
            });
        }
    },

    /**
     * Function to perform the RPC call to get acquirer fees.
     *
     * @private
     * @param cacheKey - Key used for cache storage
     * @param {Object} params - Parameters for the RPC call
     * @returns {Promise}
     */
    _getAcquirerFees: function(cacheKey, params) {
        return this._rpc({
            route: '/donation/get_acquirer_fees',
            params: params,
        });
    },
});
