import { _t } from "@web/core/l10n/translation";
import { PaymentInterface } from "@point_of_sale/app/payment/payment_interface";
import { ConfirmationDialog, AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { register_payment_method } from "@point_of_sale/app/store/pos_store";
import * as kpay from "@pos_kpay/app/kpay";

const OCTOPUS_PAYMENT_TYPES = ["4", "5"];
export class PaymentKpay extends PaymentInterface {
    static terminalInstances = new Map();

    setup() {
        super.setup(...arguments);

        const terminalIpAddress = this.payment_method_id.kpay_terminal_ip_address;
        const appId = this.payment_method_id.kpay_app_id;
        const appSecret = this.payment_method_id.kpay_app_secret;

        const terminalKey = `${terminalIpAddress}-${appId}`;
        let terminalData = PaymentKpay.terminalInstances.get(terminalKey);

        if (!terminalData) {
            const settings = new kpay.KpaySettings();
            settings.terminalIpAddress = terminalIpAddress;
            settings.appId = appId;
            settings.appSecret = appSecret;

            const newTerminal = new kpay.KpayTerminal(settings);
            const newSignPromise = this._kpay_sign(newTerminal, true);

            terminalData = {
                terminal: newTerminal,
                signPromise: newSignPromise,
            };
            PaymentKpay.terminalInstances.set(terminalKey, terminalData);
        }

        this.terminal = terminalData.terminal;
        this._kpaySignPromise = terminalData.signPromise;

        this.paymentLineResolvers = {};
    }

    send_payment_request(uuid) {
        super.send_payment_request(...arguments);
        return this._kpay_pay(uuid);
    }

    send_payment_cancel(order, uuid) {
        super.send_payment_cancel(order, uuid);
        return this._kpay_cancel();
    }

    pending_kpay_line() {
        return this.pos.getPendingPaymentLine("kpay");
    }

    _handle_connection_failure(data = {}) {
        const line = this.pending_kpay_line();
        if (line) {
            line.set_payment_status("retry");
        }
        console.error("KPay connection error: ", data);
        this._showError(_t("Connection to KPay failed"));

        return false;
    }
    _generate_terminal_request_id() {
        this.terminalRequestId = Math.random().toString(36).substring(2, 12);
        return this.terminalRequestId;
    }

    _kpay_sign(terminalInstance, ignore_error = false) {
        return terminalInstance.sign(ignore_error).then((data) => {
            if (!data) {
                !ignore_error && this._handle_connection_failure();
                return false;
            }
            return this._odoo_set_kpay_public_key(
                this.payment_method_id.id,
                terminalInstance.publicKey
            );
        });
    }

    _odoo_set_kpay_public_key(payment_method_id, public_key) {
        return this.pos.data.silentCall("pos.payment.method", "kpay_set_public_key", [
            [payment_method_id],
            public_key,
        ]);
    }

    _kpay_pay(uuid, retry = 0) {
        return this._kpaySignPromise
            .then(() => {
                const order = this.pos.get_order();
                const line = order.get_selected_paymentline();
                if (!line) {
                    this._showError(_t("No payment line selected"));
                    return Promise.resolve(false);
                }

                if (line.amount <= 0) {
                    if (OCTOPUS_PAYMENT_TYPES.includes(this.payment_method_id.kpay_payment_type)) {
                        this._showError(_t("Void/refund of Octopus payments are not supported"));
                        return Promise.resolve(false);
                    }
                    return new Promise((resolve) => {
                        this.env.services.dialog.add(ConfirmationDialog, {
                            title: _t("Void/Refund"),
                            body: _t(
                                "On the Kpay terminal,\n" +
                                    "• Voiding Card payments generates refund order in Odoo.\n" +
                                    "• Voiding other type payments and refunding of all payments require creating refund order in Odoo."
                            ),
                            confirm: () => resolve(true),
                            confirmLabel: _t("Proceed"),
                            cancel: () => resolve(false),
                        });
                    });
                }

                const rounding = this.pos.currency.rounding;
                const payAmount = Math.round(line.amount / rounding);
                const tipsAmount = Math.round(order.get_tip() / rounding);
                const payload = {
                    includeReceipt: true,
                    outTradeNo: order.pos_reference + "-" + this._generate_terminal_request_id(),
                    payAmount: String(payAmount).padStart(12, "0"),
                    tipsAmount: String(tipsAmount).padStart(12, "0"),
                    payCurrency: order.currency.iso_numeric.toString(),
                    callbackUrl: `${this.pos.session._base_url}/pos_kpay/${this.payment_method_id.kpay_app_id}/notification`,
                };
                if (this.payment_method_id.kpay_payment_type) {
                    if (
                        OCTOPUS_PAYMENT_TYPES.includes(this.payment_method_id.kpay_payment_type) &&
                        line.amount < 0.1
                    ) {
                        this._showError(_t("Minimum transaction amount for Octopus is 0.1"));
                        return Promise.resolve(false);
                    }
                    payload.paymentType = this.payment_method_id.kpay_payment_type;
                    payload.callbackUrl = `${this.pos.session._base_url}/pos_kpay/${this.payment_method_id.kpay_app_id}-${this.payment_method_id.kpay_payment_type}/notification`;
                }

                return this._odoo_set_kpay_public_key(
                    this.payment_method_id.id,
                    this.terminal.publicKey
                ).then(() => {
                    return this.terminal.sales(payload).then((data) => {
                        // 40004: Signature expired, need to re-sign, retry up to 3 times
                        if (data.code === 40004) {
                            if (retry < 3) {
                                console.warn(
                                    `KPay: Signature expired, retrying... (attempt ${
                                        retry + 1
                                    } of 3)`
                                );
                                return this._kpay_sign(this.terminal, true).then(() => {
                                    return this._kpay_pay(uuid, retry + 1);
                                });
                            } else {
                                console.error("KPay: Signature expired, retry limit reached");
                            }
                        }
                        return this._kpay_handle_response(data);
                    });
                });
            })
            .catch((error) => this._handle_connection_failure(error));
    }

    _kpay_cancel() {
        return this._kpaySignPromise.then(() => {
            const order = this.pos.get_order();
            return this.terminal.close({
                outTradeNo: order.pos_reference + "-" + this.terminalRequestId,
            });
        });
    }

    _kpay_handle_response(result) {
        const line = this.pending_kpay_line();

        if (result.code !== 10000) {
            console.error("error from KPay: ", result);

            this._showError(
                _t("An unexpected error occurred. Message from KPay: ") + result.message
            );
            if (line) {
                line.set_payment_status("force_done");
            }
            return false;
        } else {
            line.set_payment_status("waitingCard");
            return this.waitForPaymentConfirmation();
        }
    }

    waitForPaymentConfirmation() {
        return new Promise((resolve) => {
            this.paymentLineResolvers[this.pending_kpay_line().uuid] = resolve;
        });
    }

    async handleKpayStatusResponse() {
        const notification = await this.pos.data.silentCall(
            "pos.payment.method",
            "get_latest_kpay_status",
            [[this.payment_method_id.id]]
        );
        if (!notification) {
            this._handle_connection_failure();
            return;
        }
        const line = this.pending_kpay_line();
        const isPaymentSuccessful = notification.payResult === 2;

        if (isPaymentSuccessful && line) {
            this.handleSuccessResponse(line, notification);
        }

        const resolver = line ? this.paymentLineResolvers?.[line.uuid] : null;
        if (resolver) {
            resolver(isPaymentSuccessful);
        } else if (line) {
            line.handle_payment_response(isPaymentSuccessful);
        }
    }

    handleSuccessResponse(line, notification) {
        const isCreditCard = Boolean(notification.refNo);
        line.payment_method_payment_mode = kpay.PAYMENT_METHODS_MAPPING[notification.payMethod];

        if (isCreditCard) {
            line.transaction_id = notification.refNo;
            line.card_brand = notification.aidLabel;
            line.card_no = (notification.cardNo && notification.cardNo.slice(-4)) || "";
        } else {
            line.transaction_id = notification.transactionNo;
        }
        this.terminalRequestId = 0;
    }

    _showError(msg, title) {
        if (!title) {
            title = _t("KPay Error");
        }
        this.env.services.dialog.add(AlertDialog, {
            title: title,
            body: msg,
        });
    }
}

register_payment_method("kpay", PaymentKpay);
