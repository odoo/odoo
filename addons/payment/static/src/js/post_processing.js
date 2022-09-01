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
            // if there's only one tx to manage
            if(countTxInState(['tx_done', 'tx_error', 'tx_pending', 'tx_authorized']) === 1) {
                var tx = render_values['tx_done'][0] || render_values['tx_authorized'][0] || render_values['tx_error'][0];
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

    return publicWidget.registry.PaymentPostProcessing;
});
