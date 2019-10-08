odoo.define('payment_ingenico.processing', function (require) {
    'use strict';

    var ajax = require('web.ajax');
    var rpc = require('web.rpc');
    var publicWidget = require('web.public.widget');

    var PaymentProcessing = publicWidget.registry.PaymentProcessing;


    return PaymentProcessing.include({
        init: function () {
            this._super.apply(this, arguments);
            this._authInProgress = false;
        },

        processPolledData: function(transactions) {
            this._super.apply(this, arguments);
            for (var itx=0; itx < transactions.length; itx++) {
                var tx = transactions[itx];
                if (tx.acquirer_provider === 'ogone' && tx.state === 'pending' && tx.html_3ds && !this._authInProgress) {
                    this._authInProgress = true;
                    $("body").html(tx.html_3ds);
                }
            }
        },
    });
});
