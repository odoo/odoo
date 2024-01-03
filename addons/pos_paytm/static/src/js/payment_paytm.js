/** @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { PaymentInterface } from "@point_of_sale/app/payment/payment_interface";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

const REQUEST_TIMEOUT = 5000;

export class PaymentPaytm extends PaymentInterface {
    /**
     * @Override
     * @param { string } uuid
     * @returns Promise
     */
    async send_payment_request(uuid) {
        await super.send_payment_request(...arguments);
        const paymentLine = this.pos.get_order()?.get_selected_paymentline();
        const order = this.pos?.get_order();
        const retry = this._retryCountUtility(order.uuid);
        let transactionId = order.name.replace(" ", "").replaceAll("-", "").toUpperCase();
        if (retry > 0) {
            transactionId = transactionId.concat("retry", retry);
        }
        const transactionAmount = paymentLine.amount * 100;
        const timeStamp = Math.floor(Date.now() / 1000);

        // Preparing Unique Random Reference Id
        const referencePrefix = this.pos.config.name.replace(/\s/g, "").slice(0, 4);
        const referenceId = referencePrefix.concat(Math.floor(Math.random() * 1000000000));
        const response = await this.makePaymentRequest(
            transactionAmount,
            transactionId,
            referenceId,
            timeStamp
        );
        if (!response) {
            paymentLine.set_payment_status("force_done");
            this._incrementRetry(order.uuid);
            return false;
        }
        paymentLine.set_payment_status("waitingCard");
        const pollResponse = await this.pollPayment(transactionId, referenceId, timeStamp);
        if (pollResponse) {
            const retry_remove = true;
            this._retryCountUtility(order.uuid, retry_remove);
            return true;
        } else {
            this._incrementRetry(order.uuid);
            return false;
        }
    }

    /**
     * @Override
     * @param {} order
     * @param { string } uuid
     * @returns Promise
     */
    async send_payment_cancel(order, uuid) {
        await super.send_payment_cancel(...arguments);
        const paymentLine = this.pos.get_order()?.get_selected_paymentline();
        paymentLine.set_payment_status("retry");
        this._incrementRetry(order.uuid);
        clearTimeout(this.pollTimeout);
        return true;
    }

    /**
     * @param { string } transactionId
     * @param { string } referenceId
     * @param { datetime } timestamp
     * @returns Promise
     */
    async pollPayment(transactionId, referenceId, timestamp) {
        const fetchPaymentStatus = async (resolve, reject) => {
            const paymentLine = this.pos.get_order()?.get_selected_paymentline();
            if (!paymentLine || paymentLine.payment_status == "retry") {
                return false;
            }
            try {
                const data = await this.pos.data.silentCall(
                    "pos.payment.method",
                    "paytm_fetch_payment_status",
                    [[this.payment_method_id.id], transactionId, referenceId, timestamp]
                );
                if (data?.error) {
                    throw data?.error;
                }
                const resultCode = data?.resultCode;
                if (resultCode === "S" && data?.merchantReferenceNo != referenceId) {
                    throw _t("Reference number mismatched");
                } else if (resultCode === "S") {
                    paymentLine.paytm_authcode = data?.authCode;
                    paymentLine.paytm_issuer_card_no = data?.issuerMaskCardNo;
                    paymentLine.paytm_issuer_bank = data?.issuingBankName;
                    paymentLine.paytm_payment_method = data?.payMethod;
                    paymentLine.card_type = data?.cardType;
                    paymentLine.paytm_card_scheme = data?.cardScheme;
                    paymentLine.paytm_reference_no = data?.merchantReferenceNo;
                    paymentLine.transactionId = data?.merchantTransactionId;
                    paymentLine.payment_date = data?.transactionDateTime;
                    return resolve(data);
                } else {
                    this.pollTimeout = setTimeout(
                        fetchPaymentStatus,
                        REQUEST_TIMEOUT,
                        resolve,
                        reject
                    );
                }
            } catch (error) {
                const order = this.pos.get_order();
                this._incrementRetry(order.uuid);
                paymentLine.set_payment_status("force_done");
                this._showError(error, "paytmFetchPaymentStatus");
                return resolve(false);
            }
        };
        return new Promise(fetchPaymentStatus);
    }
    /**
     * @param { float } amount
     * @param { string } transactionId
     * @param { string } referenceId
     * @param { datetime } timestamp
     * @returns Promise
     */
    async makePaymentRequest(amount, transactionId, referenceId, timestamp) {
        try {
            const data = await this.pos.data.silentCall(
                "pos.payment.method",
                "paytm_make_payment_request",
                [[this.payment_method_id.id], amount, transactionId, referenceId, timestamp]
            );
            if (data?.error) {
                throw data.error;
            }
            return data;
        } catch (error) {
            this._showError(error, "paytmMakePaymentRequest");
            return false;
        }
    }

    // ---------------------------------------------------------------------------
    // Private methods
    // ---------------------------------------------------------------------------

    _retryCountUtility(uuid, remove = false) {
        if (remove) {
            localStorage.removeItem(uuid);
        } else {
            return localStorage.getItem(uuid) || (localStorage.setItem(uuid, 0) && 0);
        }
    }

    _incrementRetry(uuid) {
        let retry = localStorage.getItem(uuid);
        localStorage.setItem(uuid, ++retry);
    }
    _showError(error_msg, title) {
        this.env.services.dialog.add(AlertDialog, {
            title: title || _t("PayTM Error"),
            body: error_msg,
        });
    }
}
