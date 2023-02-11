odoo.define('payment.post_processing', function (require) {
    'use strict';

    var publicWidget = require('web.public.widget');
    var core = require('web.core');
    const {Markup} = require('web.utils');

    var _t = core._t;

    $.blockUI.defaults.css.border = '0';
    $.blockUI.defaults.css["background-color"] = '';
    $.blockUI.defaults.overlayCSS["opacity"] = '0.9';

    publicWidget.registry.PaymentPostProcessing = publicWidget.Widget.extend({
        selector: 'div[name="o_payment_status"]',
        xmlDependencies: ['/payment/static/src/xml/payment_post_processing.xml'],

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
            this._rpc({
                route: '/payment/status/poll',
                params: {
                    'csrf_token': core.csrf_token,
                }
            }).then(function(data) {
                if(data.success === true) {
                    self.processPolledData(data.display_values_list);
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
        processPolledData: function (display_values_list) {
            var render_values = {
                'tx_draft': [],
                'tx_pending': [],
                'tx_authorized': [],
                'tx_done': [],
                'tx_cancel': [],
                'tx_error': [],
            };

            if (display_values_list.length > 0) {
                // In almost every cases there will be a single transaction to display. If there are
                // more than one transaction, the last one will most likely be the one that was
                // confirmed. We use this one to redirect the user to the final page.
                window.location = display_values_list[0].landing_route;
                return;
            }

            // group the transaction according to their state
            display_values_list.forEach(function (display_values) {
                var key = 'tx_' + display_values.state;
                if(key in render_values) {
                    if (display_values["display_message"]) {
                        display_values.display_message = Markup(display_values.display_message)
                    }
                    render_values[key].push(display_values);
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
                       
            /*
            * When the server sends the list of monitored transactions, it tries to post-process 
            * all the successful ones. If it succeeds or if the post-process has already been made, 
            * the transaction is removed from the list of monitored transactions and won't be 
            * included in the next response. We assume that successful and post-process 
            * transactions should always prevail on others, regardless of their number or state.
            */
            if (render_values['tx_done'].length === 1 &&
                render_values['tx_done'][0].is_post_processed) {
                    window.location = render_values['tx_done'][0].landing_route;
                    return;
            }
            // If there are multiple transactions monitored, display them all to the customer. If
            // there is only one transaction monitored, redirect directly the customer to the
            // landing route.
            if(countTxInState(['tx_done', 'tx_error', 'tx_pending', 'tx_authorized']) === 1) {
                // We don't want to redirect customers to the landing page when they have a pending
                // transaction. The successful transactions are dealt with before.
                var tx = render_values['tx_authorized'][0] || render_values['tx_error'][0];
                if (tx) {
                    window.location = tx.landing_route;
                    return;
                }
            }

            this.displayContent("payment.display_tx_list", render_values);
        },
        displayContent: function (xmlid, render_values) {
            var html = core.qweb.render(xmlid, render_values);
            $.unblockUI();
            this.$el.find('div[name="o_payment_status_content"]').html(html);
        },
        displayLoading: function () {
            var msg = _t("We are processing your payment, please wait ...");
            $.blockUI({
                'message': '<h2 class="text-white"><img src="/web/static/img/spin.png" class="fa-pulse"/>' +
                    '    <br />' + msg +
                    '</h2>'
            });
        },
    });
});
