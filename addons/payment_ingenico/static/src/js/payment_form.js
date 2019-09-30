odoo.define('payment_ogone.payment_form', function (require) {
    "use strict";
    
    // var ajax = require('web.ajax');
    var core = require('web.core');
    // var Dialog = require('web.Dialog');
    // var Widget = require('web.Widget');
    var PaymentForm = require('payment.payment_form');
    // var qweb = core.qweb;
    // var _t = core._t;

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
        _OgoneTransaction: function (ev, $checkedRadio, addPmEvent) {
            var self = this;
            var acquirerID = this.getAcquirerIdFromRadio($checkedRadio);
            var acquirerForm = this.$('#o_payment_add_token_acq_' + acquirerID);
            var inputsForm = $('input', acquirerForm);
            // var ds = $('input[name="data_set"]', acquirerForm)[0];
            var formData = this.getFormData(inputsForm);
            var $ProcessingForm = $('#payment_method')
            var processData = this.getFormData($('input', $ProcessingForm));
            delete processData['cc_brand'];
            delete processData['cc_cvc'];
            delete processData['cc_expiry'];
            delete processData['cc_holder_name'];
            delete processData['csrf_token'];
            delete processData['cc_number'];

            var paramPlus = (this.options.partnerId) ? {'partner_id': this.options.partnerId} : {'partner_id': null};
            paramPlus['acquirerId'] = acquirerID;
            paramPlus['browserColorDepth'] = screen.colorDepth;
            paramPlus['browserJavaEnabled'] =  navigator.javaEnabled();
            paramPlus['browserLanguage'] = navigator.language;
            paramPlus['browserScreenHeight'] = screen.height;
            paramPlus['browserScreenWidth'] = screen.width;
            paramPlus['browserTimeZone'] = new Date().getTimezoneOffset();
            paramPlus['browserUserAgent'] = navigator.userAgent;
            paramPlus['FLAG3D'] = 'Y',
            paramPlus['WIN3DS'] = 'MAINW'; // 'POPUP';
            paramPlus['return_url'] = formData['return_url'];
            paramPlus['form_values'] = processData;
            paramPlus['form_action_url'] = this.el["action"];
            self._rpc({
                route: '/payment/ogone/prepare_token',
                params: paramPlus
            }).then(function (result) {
                result['CVC'] = formData.cc_cvc;
                result['CARDNO'] = formData.cc_number.replace(/\s/g, '');
                result['ED'] = formData.cc_expiry.replace(/\s\/\s/g, '');
                result['CN'] = formData.cc_holder_name;
                var wrongInput = false;
                inputsForm.toArray().forEach(function (element) {
                    //skip the check of non visible inputs
                    if ($(element).attr('type') === 'hidden') {
                        return true;
                    }
                    var message;
                    $(element).closest('div.form-group').removeClass('o_has_error').find('.form-control, .custom-select').removeClass('is-invalid');
                    $(element).siblings(".o_invalid_field").remove();
                    //force check of forms validity (useful for Firefox that refill forms automatically on f5)
                    $(element).trigger("focusout");
                    if (element.dataset.isRequired && element.value.length === 0) {
                            $(element).closest('div.form-group').addClass('o_has_error').find('.form-control, .custom-select').addClass('is-invalid');
                            message = '<div style="color: red" class="o_invalid_field" aria-invalid="true">' + _.str.escapeHTML("The value is invalid.") + '</div>';
                            $(element).closest('div.form-group').append(message);
                            wrongInput = true;
                    } else if ($(element).closest('div.form-group').hasClass('o_has_error')) {
                        wrongInput = true;
                         message = '<div style="color: red" class="o_invalid_field" aria-invalid="true">' + _.str.escapeHTML("The value is invalid.") + '</div>';
                        $(element).closest('div.form-group').append(message);
                    }
            });

            if (wrongInput) {
                return;
            }
            var APIUrl = result['api_url'];
            delete result['api_url'];
            var ogoneForm = document.createElement("form");
            ogoneForm.method = "POST";
            ogoneForm.action = APIUrl;
            var el = document.createElement("input");
            el.setAttribute('type', 'submit');
            el.setAttribute('name', "Submit");
            ogoneForm.appendChild(el);
            _.each(result, function (value, key) {
                var el = document.createElement("input");
                el.setAttribute('type', 'hidden');
                el.setAttribute('value', value);
                el.setAttribute('name', key);
                ogoneForm.appendChild(el);
            });
            document.body.appendChild(ogoneForm);
            ogoneForm.submit();
            });
        },

        /**
         * @override
         */
        updateNewPaymentDisplayStatus: function () {
            var $checkedRadio = this.$('input[type="radio"]:checked');
            var acquirerId = this.getAcquirerIdFromRadio($checkedRadio);
            if ($checkedRadio.length !== 1) {
                return;
            }
    
            //  hide add token form for ngenico
            if ($checkedRadio.data('provider') === 'ogone' && this.isNewPaymentRadio($checkedRadio)) {
                //this.$('[id*="o_payment_add_token_acq_"]');
                this.$('#o_payment_add_token_acq_' + acquirerId).removeClass('d-none');
            } else {
                this._super.apply(this, arguments);
            }
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
            // first we check that the user has selected a Ogone as s2s payment method
            if ($checkedRadio.length === 1 && this.isNewPaymentRadio($checkedRadio) && $checkedRadio.data('provider') === 'ogone') {
                this._OgoneTransaction(ev, $checkedRadio);
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
    
            // first we check that the user has selected a Ogone as add payment method
            if ($checkedRadio.length === 1 && this.isNewPaymentRadio($checkedRadio) && $checkedRadio.data('provider') === 'ogone') {
                this._OgoneTransaction(ev, $checkedRadio, true);
            } else {
                this._super.apply(this, arguments);
            }
        },
    });
    return PaymentForm;
    });
