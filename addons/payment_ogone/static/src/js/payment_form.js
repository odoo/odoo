// odoo.define('payment_ogone.connect', function (require) {
//     "use strict";
//     var ajax = require('web.ajax');
//     var connect = ajax.loadJS ("/payment_ogone/static/lib/connectsdknoEncrypt.js");
// });


odoo.define('payment_ogone.payment_form', function (require) {
    "use strict";
    
    var ajax = require('web.ajax');
    var core = require('web.core');
    var Dialog = require('web.Dialog');
    var Widget = require('web.Widget');
    var PaymentForm = require('payment.payment_form');
    // ajax.loadJS("/payment_ogone/static/lib/connectsdknoEncrypt.js");
       
    var qweb = core.qweb;
    var _t = core._t;
    // ajax.loadXML('/payment_ogone/static/src/xml/ogone_templates.xml', qweb);
    
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
            var ds = $('input[name="data_set"]', acquirerForm)[0];

            if (this.options.partnerId === undefined) {
                console.warn('payment_form: unset partner_id when adding new token; things could go wrong');
            }
            var formData = this.getFormData(inputsForm);
            console.log(formData);

            self._rpc({
                model: 'payment.token',
                method: 'ogone_prepare_token',
                context: self.context,
            }).then(function (result) {

                result['CVC'] = formData.cc_cvc;
                result['CARDNO'] = formData.cc_number.replace(/\s/g, '');
                result['ED'] = formData.cc_expiry.replace(/\s\/\s/g, '');
                result['CN'] = formData.cc_holder_name;
                result['PARAMPLUS'] = "test1=0&test2=coucou&test3=5";
                

                // TEST if INPUT FORM IS VALID
                var APIUrl = "https://ogone.test.v-psp.com/ncol/test/alias_gateway.asp";
                console.log(result); // { PaymentSha: paymentDetails}    

                var ogoneForm = document.createElement("form");
                ogoneForm.method = "POST";
                ogoneForm.action = APIUrl;
                var el = document.createElement("input");
                el.setAttribute('type', 'submit');
                el.setAttribute('name', "Submit");
                ogoneForm.appendChild(el);
                _.each(result, function (key, value) {
                    var el = document.createElement("input");
                    el.setAttribute('type', 'hidden');
                    el.setAttribute('value', key);
                    el.setAttribute('name', value);
                    ogoneForm.appendChild(el);
                });
                document.body.appendChild(ogoneForm);
                ogoneForm.submit();

            });
            
            // todo: get url from parameters with other fields
            // FLOW:
            // STEP 0
            // GET THE NEEDED INFORMATION FROM THE BACKEND;
            // ACCEPTURL
            // ALIASPERSISTEDAFTERUSE
            // EXCEPTIONURL
            // ORDERID
            // PSPID
            // SHASIGN : for 
            // PARAMPLUS
            // STEP 1
            // Create the Token which is named Alias in Ingenico denomination. This alias is created when submitting this form.(Pay Now)
            // The alias creation depends on the following fields:
            // ACCEPTURL
            // ALIASPERSISTEDAFTERUSE
            // CARDNO
            // CN
            // CVC
            // ED=1223
            // EXCEPTIONURL=
            // ORDERID=STDREF123
            // PSPID=OOAPI
            // SHASIGN= xxx
            // These fields are availaible in the backend.


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
    
            //  hide add token form for ogone
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
            // first we check that the user has selected a ogone as s2s payment method
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
    //debugger;
    return PaymentForm;
    });
