/** @odoo-module */
/* global timapi */

import { Gui } from "@point_of_sale/js/Gui";
import core from "web.core";
import PaymentInterface from "@point_of_sale/js/payment";

var _t = core._t;

window.onTimApiReady = function () {};
window.onTimApiPublishLogRecord = function (record) {
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

        var terminal_ip = this.payment_method.six_terminal_ip;
        var instanced_payment_method = _.find(this.pos.payment_methods, function (payment_method) {
            return (
                payment_method.use_payment_terminal === "six" &&
                payment_method.six_terminal_ip === terminal_ip &&
                payment_method.payment_terminal
            );
        });
        if (instanced_payment_method !== undefined) {
            var payment_terminal = instanced_payment_method.payment_terminal;
            this.terminal = payment_terminal.terminal;
            this.terminalListener = payment_terminal.terminalListener;
            return;
        }

        var settings = new timapi.TerminalSettings();
        settings.connectionMode = timapi.constants.ConnectionMode.onFixIp;
        settings.connectionIPString = this.payment_method.six_terminal_ip;
        settings.connectionIPPort = "80";
        settings.integratorId = "175d97a0-2a88-4413-b920-e90037b582ac";
        settings.dcc = false;

        this.terminal = new timapi.Terminal(settings);
        this.terminal.setPosId(this.pos.pos_session.name);
        this.terminal.setUserId(this.pos.pos_session.user_id[0]);

        this.terminalListener = new timapi.DefaultTerminalListener();
        this.terminalListener.transactionCompleted = this._onTransactionComplete.bind(this);
        this.terminalListener.balanceCompleted = this._onBalanceComplete.bind(this);
        this.terminal.addListener(this.terminalListener);

        var recipients = [
            timapi.constants.Recipient.merchant,
            timapi.constants.Recipient.cardholder,
        ];
        var options = [];
        _.forEach(recipients, (recipient) => {
            var option = new timapi.PrintOption(
                recipient,
                timapi.constants.PrintFormat.normal,
                45,
                [
                    timapi.constants.PrintFlag.suppressHeader,
                    timapi.constants.PrintFlag.suppressEcrInfo,
                ]
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
    send_payment_request: function () {
        this._super.apply(this, arguments);
        this.pos.get_order().selected_paymentline.set_payment_status("waitingCard");
        return this._sendTransaction(timapi.constants.TransactionType.purchase);
    },

    /**
     * @override
     */
    send_payment_reversal: function () {
        this._super.apply(this, arguments);
        this.pos.get_order().selected_paymentline.set_payment_status("reversing");
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
            if (event.exception.resultCode !== timapi.constants.ResultCode.apiCancelEcr) {
                Gui.showPopup("ErrorPopup", {
                    title: _t("Transaction was not processed correctly"),
                    body: event.exception.errorText,
                });
            }

            this.transactionResolve();
        } else {
            if (data.printData) {
                this._printReceipts(data.printData.receipts);
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
            Gui.showPopup("ErrorPopup", {
                title: _t("Balance Failed"),
                body: _t("The balance operation failed."),
            });
        } else {
            this._printReceipts(data.printData.receipts);
        }
    },

    _printReceipts: function (receipts) {
        _.forEach(receipts, (receipt) => {
            var value = receipt.value.replace(/\n/g, "<br />");
            if (
                receipt.recipient === timapi.constants.Recipient.merchant &&
                this.pos.env.proxy.printer
            ) {
                this.pos.env.proxy.printer.print_receipt(
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
            Math.round(
                this.pos.get_order().selected_paymentline.amount / this.pos.currency.rounding
            ),
            timapi.constants.Currency[this.pos.currency.name],
            this.pos.currency.decimal_places
        );

        return new Promise((resolve) => {
            this.transactionResolve = resolve;
            this.terminal.transactionAsync(transactionType, amount);
        });
    },
});

export default PaymentSix;
