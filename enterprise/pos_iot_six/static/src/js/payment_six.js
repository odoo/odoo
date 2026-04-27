/** @odoo-module */
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { PaymentWorldline } from "@pos_iot/app/payment";
import { _t } from "@web/core/l10n/translation";

export class PaymentSix extends PaymentWorldline {
    setup() {
        super.setup(...arguments);
        this.enable_reversals();
    }

    get_payment_data(uuid) {
        const paymentline = this.pos.get_order().get_paymentline_by_uuid(uuid);
        const pos = this.pos;
        return {
            messageType: "Transaction",
            transactionType: paymentline.transactionType,
            amount: Math.abs(Math.round(paymentline.amount * 100)),
            currency: pos.currency.name,
            cid: uuid,
            posId: pos.session.name,
            userId: pos.user.id,
        };
    }

    send_payment_request(uuid) {
        const paymentline = this.pos.get_order().get_paymentline_by_uuid(uuid);
        paymentline.transactionType = paymentline.amount < 0 ? "Refund" : "Payment";

        return super.send_payment_request(uuid);
    }

    send_payment_reversal(uuid) {
        const paymentline = this.pos.get_order().get_paymentline(uuid);
        paymentline.transactionType = "Refund";
        return super.send_payment_request(uuid);
    }

    _onBalanceComplete(data) {
        if (data.Error || !data.Ticket) {
            const error_msg =
                data.Error && data.Error != ""
                    ? data.Error
                    : _t("Failed to get balance report from the terminal. Please retry.");
            this.env.services.dialog.add(AlertDialog, {
                title: _t("Six balance report error"),
                body: error_msg,
            });
            return;
        }
        const wrapper = document.createElement("div");
        wrapper.innerHTML = `<div class='pos-receipt'>
                <div class='pos-payment-terminal-receipt' style='font-size: 32px;'>
                    ${data.Ticket.replace(/\n/g, "<br>")}
                </div>
            </div>`;
        const element = wrapper.firstElementChild;
        this.pos.hardwareProxy.printer.printReceipt(element);
    }

    async sendBalance() {
        var self = this;
        const terminal_proxy = self.get_terminal();
        if (!terminal_proxy) {
            this._showErrorConfig();
            return false;
        }
        const printer = this.pos.hardwareProxy.printer;
        if (!printer) {
            this.env.services.dialog.add(AlertDialog, {
                title: _t("No printer configured"),
                body: _t(
                    "You must select a printer in your POS config to print Six balance report"
                ),
            });
            return false;
        }

        terminal_proxy.addListener(self._onBalanceComplete.bind(self));
        return terminal_proxy.action({
            messageType: "Balance",
            posId: self.pos.session.id,
            userId: self.pos.session.user_id.id,
        });
    }
}
