odoo.define('payment.processing', function (require) {
    'use strict';

    var publicWidget = require('web.public.widget');
    var ajax = require('web.ajax');
    var core = require('web.core');

    var _t = core._t;

    $.blockUI.defaults.css.border = '0';
    $.blockUI.defaults.css["background-color"] = '';
    $.blockUI.defaults.overlayCSS["opacity"] = '0.9';

    publicWidget.registry.PaymentProcessing = publicWidget.Widget.extend({
        selector: '.o_payment_processing',
        xmlDependencies: ['/payment/static/src/xml/payment_processing.xml'],

        _pollCount: 0,

        start: function() {
            this.displayLoading();
            this.poll();
            return this._super.apply(this, arguments);
        },
        /* Methods */
        startPolling: function () {
            var timeout = 3000;
            //
            if(this._pollCount >= 10 && this._pollCount < 20) {
                timeout = 10000;
            }
            else if(this._pollCount >= 20) {
                timeout = 30000;
            }
            //
            setTimeout(this.poll.bind(this), timeout);
            this._pollCount ++;
        },
        poll: function () {
            var self = this;
            ajax.jsonRpc('/payment/process/poll', 'call', {}).then(function(data) {
                if(data.success === true) {
                    self.processPolledData(data.transactions);
                }
                else {
                    switch(data.error) {
                    case "tx_process_retry":
                        break;
                    case "no_tx_found":
                        self.displayContent("payment.no_tx_found", {});
                        break;
                    default: // if an exception is raised
                        self.displayContent("payment.exception", {exception_msg: data.error});
                        break;
                    }
                }
                self.startPolling();

            }).guardedCatch(function() {
                self.displayContent("payment.rpc_error", {});
                self.startPolling();
            });
        },
        processPolledData: function (transactions) {
            var render_values = {
                'tx_draft': [],
                'tx_pending': [],
                'tx_authorized': [],
                'tx_done': [],
                'tx_cancel': [],
                'tx_error': [],
            };

            if (transactions.length > 0 && ['transfer', 'sepa_direct_debit'].indexOf(transactions[0].acquirer_provider) >= 0) {
                window.location = transactions[0].return_url;
                return;
            }

            // group the transaction according to their state
            transactions.forEach(function (tx) {
                var key = 'tx_' + tx.state;
                if(key in render_values) {
                    render_values[key].push(tx);
                }
            });

            function countTxInState(states) {
                var nbTx = 0;
                for (var prop in render_values) {
                    if (states.indexOf(prop) > -1 && render_values.hasOwnProperty(prop)) {
                        nbTx += render_values[prop].length;
                    }
                }
                return nbTx;
            }
            // if there's only one tx to manage
            if(countTxInState(['tx_done', 'tx_error', 'tx_pending']) === 1) {
                var tx = render_values['tx_done'][0] || render_values['tx_error'][0];
                if (tx) {
                    window.location = tx.return_url;
                    return;
                }
            }

            this.displayContent("payment.display_tx_list", render_values);
        },
        displayContent: function (xmlid, render_values) {
            var html = core.qweb.render(xmlid, render_values);
            $.unblockUI();
            this.$el.find('.o_payment_processing_content').html(html);
        },
        displayLoading: function () {
            var msg = _t("We are processing your payment, please wait ...");
            $.blockUI({
                'message': '<h2 class="text-white"><img src="/web/static/src/img/spin.png" class="fa-pulse"/>' +
                    '    <br />' + msg +
                    '</h2>'
            });
        },
    });
});
