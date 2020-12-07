odoo.define('pos_six.payment', function (require) {
"use strict";

var core = require('web.core');
var { PaymentInterface, registerImplementation } = require('point_of_sale.PaymentInterface');

var _t = core._t;

// These are overrides of timapi methods.
onTimApiReady = function () {};
onTimApiPublishLogRecord = function (record) {
    // Log only warning or errors
    if (record.matchesLevel(timapi.LogRecord.LogLevel.warning)) {
        timapi.log(String(record));
    }
};

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
        this.terminal.setPosId(this.model.session.name);
        this.terminal.setUserId(this.model.session.user_id);

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
        this.terminal.setPrintOptions(options);
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
    send_payment_request: async function (paymentId) {
        this._super.apply(this, arguments);
        const payment = this.model.getRecord('pos.payment', paymentId);
        await this.model.noMutexActionHandler({ name: 'actionSetPaymentStatus', args: [payment, 'waitingCard'] })
        return this._sendTransaction(timapi.constants.TransactionType.purchase, payment);
    },

    /**
     * @override
     */
    send_payment_reversal: function (paymentId) {
        this._super.apply(this, arguments);
        const payment = this.model.getRecord('pos.payment', paymentId);
        this.model.noMutexActionHandler({ name: 'actionSetPaymentStatus', args: [payment, 'reversing'] })
        return this._sendTransaction(timapi.constants.TransactionType.reversal, payment);
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
            if (event.exception.resultCode !== timapi.constants.ResultCode.apiCancelEcr) {
                this.model.ui.askUser('ErrorPopup', {
                    title: _t('Transaction was not processed correctly'),
                    body: event.exception.errorText,
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
            this.terminal.setTransactionData(transactionData);

            this.transactionResolve(true);
        }
    },

    _onBalanceComplete: function (event, data) {
        if (event.exception) {
            this.model.ui.askUser('ErrorPopup',{
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
            if (receipt.recipient === timapi.constants.Recipient.merchant && this.model.proxy.printer) {
                this.model.proxy.printer.print_receipt(
                    "<div class='pos-receipt'><div class='pos-payment-terminal-receipt'>" +
                        value +
                    "</div></div>"
                );
            } else if (receipt.recipient === timapi.constants.Recipient.cardholder) {
                const activeOrder = this.model.getActiveOrder();
                const activePayment = this.model.getActivePayment(activeOrder);
                this.model.noMutexActionHandler({ name: 'actionSetReceiptInfo', args: [activePayment, value] });
            }
        });
    },

    _sendTransaction: function (transactionType, payment) {
        var amount = new timapi.Amount(
            Math.round(payment.amount / this.model.currency.rounding),
            timapi.constants.Currency[this.model.currency.name],
            this.model.currency.decimals
        );

        return new Promise((resolve) => {
            this.transactionResolve = resolve;
            this.terminal.transactionAsync(transactionType, amount);
        });
    },
});

registerImplementation('six', PaymentSix);

return PaymentSix;

});
