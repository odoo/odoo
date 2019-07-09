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
            //console.log(acquirerID.val());
            //console.log(inputsForm);
            // OPERATION:
                // Possible values:
    
                // RES: request for authorization
                // SAL: request for direct sale
                // RFD: refund, not linked to a previous payment, so not a maintenance operation on an existing transaction 
                // (you can not use this operation without specific permission from your acquirer).
                // PAU: Request for pre-authorization:
            var formData = this.getFormData(inputsForm);
            debugger;
            console.log(formData);
            var inputDict = {
                ACCEPTURL : "https://www.myshop.com/ok.html ",
                AMOUNT: 10500,
                CURRENCY: "EUR",
                EXCEPTIONURL: "www.error.com/notok.html",
                ORDERID: "SO55",
                OPERATION: "SAL",
                PSPID: "pinky",
                PARAMPLUS: "https:///plop.com/payment/return/",
                USERID: "OOAPI",
                PSWD: "R!ci/6Nu8a",
            };
            var paymentDetails = {
                CARDNO: formData.cc_number,
                CVC: formData.cc_cvc,
                ED: formData.cc_expiracy,
                // isRecurring: false,
                CN: formData.cc_holder_name,
                // partner_id,
                // COM, "Ceci est la description de l' order"
                // EMAIL: "mitchel@example.com",
            };
            var APIUrl = "https://ogone.test.v-psp.com/ncol/test/alias_gateway.asp";
            var params = Object.assign({}, inputDict, paymentDetails);
            console.log(params); // { PaymentSha: paymentDetails}    
            const req = new XMLHttpRequest();
            var plop = req.open("POST", APIUrl, true);
            req.setRequestHeader('Content-type', 'application/x-www-form-urlencoded');
            req.onreadystatechange = function() {//Call a function when the state changes.
                if (req.readyState == 4 && req.status == 200) {
                    console.log(req.responseText);
                }
            };
            req.send(params);
            debugger;
            // return this._rpc({
            //     route: ds.dataset.createRoute,
            //     params: rpcDict,
            // }).then(function (data) {
                
            // });


           
            
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
