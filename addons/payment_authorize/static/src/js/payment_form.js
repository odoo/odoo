odoo.define('payment_authorize.payment_form', function (require) {
"use strict";

var ajax = require('web.ajax');
var core = require('web.core');
var PaymentForm = require('payment.payment_form');

var _t = core._t;

PaymentForm.include({

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * called when clicking on pay now or add payment event to create token for credit card/debit card.
     *
     * @private
     * @param {Event} ev
     * @param {DOMElement} checkedRadio
     * @param {Boolean} addPmEvent
     */
    _createAuthorizeToken: function (ev, $checkedRadio, addPmEvent) {
        var self = this;
        if (ev.type === 'submit') {
            var button = $(ev.target).find('*[type="submit"]')[0]
        } else {
            var button = ev.target;
        }
        this.disableButton(button);
        var acquirerID = this.getAcquirerIdFromRadio($checkedRadio);
        var acquirerForm = this.$('#o_payment_add_token_acq_' + acquirerID);
        var inputsForm = $('input', acquirerForm);
        var formData = self.getFormData(inputsForm);
        if (this.options.partnerId === undefined) {
            console.warn('payment_form: unset partner_id when adding new token; things could go wrong');
        }
        var AcceptJs = false;
        if (formData.acquirer_state === 'enabled') {
            AcceptJs = 'https://js.authorize.net/v3/AcceptUI.js';
        } else {
            AcceptJs = 'https://jstest.authorize.net/v3/AcceptUI.js';
        }

        window.responseHandler = function (response) {
            _.extend(formData, response);

            if (response.messages.resultCode === "Error") {
                var errorMessage = "";
                _.each(response.messages.message, function (message) {
                    errorMessage += message.code + ": " + message.text;
                })
                acquirerForm.removeClass('d-none');
                self.enableButton(button);
                return self.displayError(_t('Server Error'), errorMessage);
            }

            self._rpc({
                route: formData.data_set,
                params: formData
            }).then (function (data) {
                if (addPmEvent) {
                    if (formData.return_url) {
                        window.location = formData.return_url;
                    } else {
                        window.location.reload();
                    }
                } else {
                    self.$el.find('input[name="save_token"]').prop('checked', self.$('#o_payment_save_token_acq_' + acquirerID).find('#o_payment_save_token').prop('checked'));
                    $checkedRadio.val(data.id);
                    self.el.submit();
                }
            }).guardedCatch(function (error) {
                // if the rpc fails, pretty obvious
                error.event.preventDefault();
                acquirerForm.removeClass('d-none');
                self.enableButton(button);
                self.displayError(
                    _t('Server Error'),
                    _t("We are not able to add your payment method at the moment.") +
                        self._parseError(error)
                );
            });
        };

        if (this.$button === undefined) {
            var params = {
                'class': 'AcceptUI d-none',
                'data-apiLoginID': formData.login_id,
                'data-clientKey': formData.client_key,
                'data-billingAddressOptions': '{"show": false, "required": false}',
                'data-responseHandler': 'responseHandler'
            };
            this.$button = $('<button>', params);
            this.$button.appendTo('body');
        }
        ajax.loadJS(AcceptJs).then(function () {
            self.$button.trigger('click');
        });
    },
    /**
     * @override
     */
    updateNewPaymentDisplayStatus: function () {
        var $checkedRadio = this.$('input[type="radio"]:checked');

        if ($checkedRadio.length !== 1) {
            return;
        }

        //  hide add token form for authorize
        if ($checkedRadio.data('provider') === 'authorize' && this.isNewPaymentRadio($checkedRadio)) {
            this.$('[id*="o_payment_add_token_acq_"]').addClass('d-none');
        }
        this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    payEvent: function (ev) {
        ev.preventDefault();
        var $checkedRadio = this.$('input[type="radio"]:checked');

        // first we check that the user has selected a authorize as s2s payment method
        if ($checkedRadio.length === 1 && this.isNewPaymentRadio($checkedRadio) && $checkedRadio.data('provider') === 'authorize') {
            this._createAuthorizeToken(ev, $checkedRadio);
        } else {
            this._super.apply(this, arguments);
        }
    },
    /**
     * @override
     */
    addPmEvent: function (ev) {
        ev.stopPropagation();
        ev.preventDefault();
        var $checkedRadio = this.$('input[type="radio"]:checked');

        // first we check that the user has selected a authorize as add payment method
        if ($checkedRadio.length === 1 && this.isNewPaymentRadio($checkedRadio) && $checkedRadio.data('provider') === 'authorize') {
            this._createAuthorizeToken(ev, $checkedRadio, true);
        } else {
            this._super.apply(this, arguments);
        }
    },
});
});
