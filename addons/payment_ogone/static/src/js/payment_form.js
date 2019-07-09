odoo.define('payment_ogone.payment_form', function (require) {
    "use strict";
    
    var ajax = require('web.ajax');
    var core = require('web.core');
    var Dialog = require('web.Dialog');
    var PaymentForm = require('payment.payment_form');
    
    var qweb = core.qweb;
    var _t = core._t;
    
    ajax.loadXML('/payment_ogone/static/src/xml/ogone_templates.xml', qweb);
    
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
        _createOgoneToken: function (ev, $checkedRadio, addPmEvent) {
            var self = this;
            var acquirerID = this.getAcquirerIdFromRadio($checkedRadio);
            var acquirerForm = this.$('#o_payment_add_token_acq_' + acquirerID);
            var inputsForm = $('input', acquirerForm);
            if (this.options.partnerId === undefined) {
                console.warn('payment_form: unset partner_id when adding new token; things could go wrong');
            }
            console.log(acquirerID);
            console.log(inputsForm);

        },
        /**
         * @override
         */
        updateNewPaymentDisplayStatus: function () {
            var $checkedRadio = this.$('input[type="radio"]:checked');
           debugger;
            if ($checkedRadio.length !== 1) {
                return;
            }
    
            //  hide add token form for ogone
            if ($checkedRadio.data('provider') === 'ogone' && this.isNewPaymentRadio($checkedRadio)) {
                this.$('[id*="o_payment_add_token_acq_"]');
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
                this._createOgoneToken(ev, $checkedRadio);
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
                this._createOgoneToken(ev, $checkedRadio, true);
            } else {
                this._super.apply(this, arguments);
            }
        },
    });
    //debugger;
    return PaymentForm;
    });
