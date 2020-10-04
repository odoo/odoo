odoo.define('pos_six.payment', function (require) {
"use strict";

var core = require('web.core');
var chrome = require('point_of_sale.chrome');
var PaymentInterface = require('point_of_sale.PaymentInterface');

var _t = core._t;

var PaymentSix = PaymentInterface.extend({

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    init: function () {
        this._super.apply(this, arguments);
        this.enable_reversals();

        var settings = new timapi.TerminalSettings();
        settings.connectionMode = timapi.constants.ConnectionMode.onFixIp;
        settings.connectionIPString = this.payment_method.six_terminal_ip;
        settings.connectionIPPort = "80";
        settings.integratorId = "175d97a0-2a88-4413-b920-e90037b582ac";
        settings.dcc = false;

        this.terminal = new timapi.Terminal(settings);
        this.terminal.posId = this.pos.pos_session.name;
        this.terminal.userId = this.pos.pos_session.user_id[0];

        this.terminalListener = new timapi.DefaultTerminalListener();
        this.terminalListener.transactionCompleted = this._onTransactionComplete.bind(this);
        this.terminalListener.balanceCompleted = this._onBalanceComplete.bind(this);
        this.terminal.addListener(this.terminalListener);

        var recipients = [timapi.constants.Recipient.merchant, timapi.constants.Recipient.cardholder];
        var options = [];
        _.forEach(recipients, (recipient) => {
            var option = new timapi.PrintOption(
                recipient,
                timapi.constants.PrintFormat.normal,
                45,
                [timapi.constants.PrintFlag.suppressHeader, timapi.constants.PrintFlag.suppressEcrInfo]
            );
            options.push(option);
        });
        this.terminal.printOptions = options;
    },

    /**
     * @override
     */
    send_payment_cancel: function () {
        this._super.apply(this, arguments);
        this.terminal.cancel();
        return Promise.resolve();
    },

    /**
     * @override
     */
    send_payment_request: function () {
        this._super.apply(this, arguments);
        this.pos.get_order().selected_paymentline.set_payment_status('waitingCard');
        return this._sendTransaction(timapi.constants.TransactionType.purchase);
    },

    /**
     * @override
     */
    send_payment_reversal: function () {
        this._super.apply(this, arguments);
        this.pos.get_order().selected_paymentline.set_payment_status('reversing');
        return this._sendTransaction(timapi.constants.TransactionType.reversal);
    },

    send_balance: function () {
        this.terminal.balanceAsync();
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    _onTransactionComplete: function (event, data) {
        timapi.DefaultTerminalListener.prototype.transactionCompleted(event, data);

        if (event.exception) {
            var line = this.pos.get_order().selected_paymentline;
            if (line && line.get_payment_status() !== 'retry') {
                this.pos.gui.show_popup('error', {
                    title: _t('Terminal Error'),
                    body: _t('Transaction was not processed correctly'),
                });
            }

            this.transactionResolve();
        } else {
            if (data.printData){
                this._printReceipts(data.printData.receipts)
            }

            // Store Transaction Data
            var transactionData = new timapi.TransactionData();
            transactionData.transSeq = data.transactionInformation.transSeq;
            this.terminal.transactionData = transactionData;

            this.transactionResolve(true);
        }
    },

    _onBalanceComplete: function (event, data) {
        if (event.exception) {
            this.pos.gui.show_popup('error',{
                'title': _t('Balance Failed'),
                'body':  _t('The balance operation failed.'),
            });
        } else {
            this._printReceipts(data.printData.receipts);
        }
    },

    _printReceipts: function (receipts) {
        _.forEach(receipts, (receipt) => {
            var value = receipt.value.replace(/\n/g, "<br />");
            if (receipt.recipient === timapi.constants.Recipient.merchant && this.pos.proxy.printer) {
                this.pos.proxy.printer.print_receipt(
                    "<div class='pos-receipt'><div class='pos-payment-terminal-receipt'>" +
                        value +
                    "</div></div>"
                );
            } else if (receipt.recipient === timapi.constants.Recipient.cardholder) {
                this.pos.get_order().selected_paymentline.set_receipt_info(value);
            }
        });
    },

    _sendTransaction: function (transactionType) {
        var amount = new timapi.Amount(
            Math.round(this.pos.get_order().selected_paymentline.amount / this.pos.currency.rounding),
            timapi.constants.Currency[this.pos.currency.name],
            this.pos.currency.decimals
        );

        return new Promise((resolve) => {
            this.transactionResolve = resolve;
            this.terminal.transactionAsync(transactionType, amount);
        });
    },
});

chrome.Chrome.include({
    // Insert "Send Balance" before Close button
    widgets: chrome.Chrome.prototype.widgets.splice(_.findIndex(chrome.Chrome.prototype.widgets, i => i.name == 'close_button'), 0, {
        name:  'balance',
        widget: chrome.HeaderButtonWidget,
        append: '.pos-rightheader',
        condition: function() { return this.pos.payment_methods.some(pm => pm.use_payment_terminal === 'six_tim'); },
        args: {
            label: _t('Send Balance'),
            action: function () {
                this.pos.payment_methods.map(pm => {
                    if (pm.use_payment_terminal === 'six_tim') {
                        pm.payment_terminal.send_balance();
                    }
                });
            }
        },
    }) && chrome.Chrome.prototype.widgets,
});

return PaymentSix;

});
