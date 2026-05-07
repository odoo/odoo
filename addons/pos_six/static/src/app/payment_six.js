/* global timapi */

import { _t } from "@web/core/l10n/translation";
import { PaymentInterface } from "@point_of_sale/app/utils/payment/payment_interface";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { registry } from "@web/core/registry";
import { escape } from "@web/core/utils/strings";

window.onTimApiReady = function () {};
window.onTimApiPublishLogRecord = function (record) {
    // Log only warning or errors
    if (record.matchesLevel(timapi.LogRecord.LogLevel.warning)) {
        timapi.log(String(record));
    }
};

// `timapi` is loaded as a separate global script and is not available at
// module-evaluation time, so the listener class is built lazily on first use.
let PaymentSixListener;
function getPaymentSixListenerClass() {
    if (!PaymentSixListener) {
        PaymentSixListener = class extends timapi.DefaultTerminalListener {
            constructor(paymentInterface) {
                super();
                this.paymentInterface = paymentInterface;
            }
            transactionCompleted(event, data) {
                super.transactionCompleted(event, data);
                this.paymentInterface._onTransactionComplete(event, data);
            }
            balanceCompleted(event, data) {
                super.balanceCompleted(event, data);
                this.paymentInterface._onBalanceComplete(event, data);
            }
        };
    }
    return PaymentSixListener;
}

export class PaymentSix extends PaymentInterface {
    setup() {
        super.setup(...arguments);

        const terminalIp = this.payment_method_id.six_terminal_ip;
        const instancedPaymentMethod = this.pos.config.payment_method_ids.find(
            (pm) =>
                pm.payment_provider === "six" &&
                pm.six_terminal_ip === terminalIp &&
                pm.payment_interface
        );
        if (instancedPaymentMethod !== undefined) {
            const paymentInterface = instancedPaymentMethod.payment_interface;
            this.terminal = paymentInterface.terminal;
            this.terminalListener = paymentInterface.terminalListener;
            return;
        }

        const settings = new timapi.TerminalSettings();
        settings.connectionMode = timapi.constants.ConnectionMode.onFixIp;
        // If no port specified -> use 80, else use the specified one
        const [host, port] = this.payment_method_id.six_terminal_ip.split(":");
        settings.connectionIPString = host;
        settings.connectionIPPort = port ? Number(port) : 80;
        settings.integratorId = "175d97a0-2a88-4413-b920-e90037b582ac";
        settings.dcc = false;

        this.terminal = new timapi.Terminal(settings);
        this.terminal.setPosId(this.pos.session.name);
        this.terminal.setUserId(this.pos.user.id);

        this.terminalListener = new (getPaymentSixListenerClass())(this);
        this.terminal.addListener(this.terminalListener);

        const recipients = [
            timapi.constants.Recipient.merchant,
            timapi.constants.Recipient.cardholder,
        ];
        const options = recipients.map(
            (recipient) =>
                new timapi.PrintOption(recipient, timapi.constants.PrintFormat.normal, 45, [
                    timapi.constants.PrintFlag.suppressHeader,
                    timapi.constants.PrintFlag.suppressEcrInfo,
                ])
        );
        this.terminal.setPrintOptions(options);
    }

    async sendPaymentCancel(line) {
        await super.sendPaymentCancel(...arguments);
        this.terminal.cancel();
        return true;
    }

    async sendPaymentRequest(line) {
        await super.sendPaymentRequest(...arguments);
        line.setPaymentStatus("waitingCard");
        const type =
            line.amount < 0
                ? timapi.constants.TransactionType.credit
                : timapi.constants.TransactionType.purchase;
        return await this._sendTransaction(type, line);
    }

    sendBalance() {
        this.terminal.balanceAsync();
    }

    _onTransactionComplete(event, data) {
        if (event.exception) {
            if (event.exception.resultCode !== timapi.constants.ResultCode.apiCancelEcr) {
                this.env.services.dialog.add(AlertDialog, {
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
            const transactionData = new timapi.TransactionData();
            transactionData.transSeq = data.transactionInformation.transSeq;
            this.terminal.setTransactionData(transactionData);

            this.transactionResolve(true);
        }
    }

    _onBalanceComplete(event, data) {
        if (event.exception) {
            this.env.services.dialog.add(AlertDialog, {
                title: _t("Balance Failed"),
                body: _t("The balance operation failed."),
            });
            return;
        }
        const merchantReceipt = Object.values(data.printData.receipts || {}).find(
            (r) => r.recipient === timapi.constants.Recipient.merchant
        );
        if (merchantReceipt) {
            this.env.services.dialog.add(AlertDialog, {
                title: _t("Balance"),
                body: merchantReceipt.value,
            });
        }
    }

    async _printReceipts(receipts) {
        const line = this.pos.getOrder()?.getSelectedPaymentline();
        if (!line) {
            return;
        }
        for (const receipt of Object.values(receipts || {})) {
            if (receipt.recipient === timapi.constants.Recipient.merchant) {
                line.setCashierReceipt(receipt.value);
            } else if (receipt.recipient === timapi.constants.Recipient.cardholder) {
                line.setReceiptInfo(receipt.value);
            }
        }
    }

    async _printReceiptText(text) {
        const container = document.getElementById("receipt-iframe-container");
        const iframe = document.createElement("iframe");
        iframe.style.width = "100%";
        iframe.style.height = "100%";
        iframe.style.border = "none";
        iframe.srcdoc = `<html><body><div id="pos-receipt"><pre style="font-family:monospace;white-space:pre-wrap;margin:0">${escape(
            text
        )}</pre></div></body></html>`;
        container.innerHTML = "";
        container.appendChild(iframe);
        await new Promise((resolve) => (iframe.onload = resolve));
        await this.pos.ticketPrinter.printWithFallback({ iframe });
    }

    // `terminal.transactionAsync` is fire-and-forget; the result is delivered
    // through the `transactionCompleted` listener. We bridge it to a promise
    // so callers can `await` the outcome.
    _sendTransaction(transactionType, line) {
        // Reversal targets a previous transaction by transSeq carried in
        // TransactionData; per the SDK docs, the amount must be undefined.
        let amount;
        if (transactionType !== timapi.constants.TransactionType.reversal) {
            amount = new timapi.Amount(
                Math.round(Math.abs(line.amount) / this.pos.currency.rounding),
                timapi.constants.Currency[this.pos.currency.name],
                this.pos.currency.decimal_places
            );
        }

        return new Promise((resolve) => {
            this.transactionResolve = resolve;
            this.terminal.transactionAsync(transactionType, amount);
        });
    }
}

registry.category("pos_payment_providers").add("six", PaymentSix);
