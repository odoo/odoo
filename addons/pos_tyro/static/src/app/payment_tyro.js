/* global TYRO */

import { loadJS } from "@web/core/assets";
import { PaymentInterface } from "@point_of_sale/app/utils/payment/payment_interface";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { TYRO_LIB_URLS } from "@pos_tyro/urls";
import { QuestionDialog } from "@pos_tyro/app/components/question_dialog";

export class PaymentTyro extends PaymentInterface {
    setup() {
        super.setup(...arguments);
        this.dialog = this.env.services.dialog;
        this.orm = this.env.services.orm;
        this.loadTyroClient();
    }

    async loadTyroClient() {
        await loadJS(TYRO_LIB_URLS[this.payment_method_id.tyro_mode]);
        const posProductInfo = await this.orm.call("pos.payment.method", "get_tyro_product_info", [
            this.payment_method_id.id,
        ]);
        this.tyroClient = new TYRO.IClient(posProductInfo.apiKey, posProductInfo);
    }

    onTransactionComplete(response, resultCallback) {
        const line = this.pos.get_order().get_selected_paymentline();
        this.dialog.closeAll();
        if (response.result === "APPROVED") {
            line.transaction_id = response.transactionId;
            line.payment_ref_no = response.transactionReference;
            line.payment_method_authcode = response.authorisationCode;
            line.card_type = response.cardType;
            line.card_no = response.elidedPan;
            if (response.customerReceipt) {
                line.set_receipt_info(response.customerReceipt);
            }
            if (response.tipAmount) {
                const tipAmount = parseInt(response.tipAmount, 10) / 100;
                if (!this.pos.config.tip_product_id) {
                    this.pos.set_tyro_surcharge(
                        tipAmount,
                        this.payment_method_id.tyro_surcharge_product_id
                    );
                    this._showError(
                        "A tip was added on the Tyro terminal, but tipping is not enabled for this Point of Sale. It will instead be recorded as a surcharge.",
                        "Tyro Warning"
                    );
                } else {
                    this.pos.set_tip(tipAmount);
                }
                line.set_amount(line.amount + tipAmount);
            }
            if (response.surchargeAmount && response.surchargeAmount !== "0.00") {
                const surchargeAmount = parseFloat(response.surchargeAmount);
                this.pos.set_tyro_surcharge(
                    surchargeAmount,
                    this.payment_method_id.tyro_surcharge_product_id
                );
                line.set_amount(line.amount + surchargeAmount);
            }
            resultCallback(true);
        } else {
            this._showError("Transaction failed - " + response.result);
            resultCallback(false);
        }
    }

    onMerchantReceiptReceived(response) {
        if (response.signatureRequired) {
            // According to Tyro docs:
            //   The POS should check for the signatureRequired boolean in the callback response,
            //   if true it means that the receipt is a signature-verification merchant copy,
            //   is not optional, and must be printed.
            this._showError("Merchant receipt printing not implemented");
        }
    }

    async send_payment_request(uuid) {
        /**
         * Override
         */
        await super.send_payment_request(...arguments);
        const line = this.pos.get_order().get_selected_paymentline();
        try {
            line.set_payment_status("waitingTyro");
            line.tyro_status = "Initiating...";
            if (line.amount < 0) {
                return new Promise((resolve) => {
                    this.tyroClient.initiateRefund(
                        {
                            amount: Math.abs(Math.round(line.amount * 100)).toString(10),
                            mid: this.payment_method_id.tyro_merchant_id,
                            tid: this.payment_method_id.tyro_terminal_id,
                            integrationKey: this.payment_method_id.tyro_integration_key,
                            integratedReceipt: this.payment_method_id.tyro_integrated_receipts,
                        },
                        {
                            receiptCallback: this.onMerchantReceiptReceived.bind(this),
                            questionCallback: (question, answerCallback) =>
                                this.dialog.add(QuestionDialog, {
                                    question,
                                    answerCallback,
                                }),
                            statusMessageCallback: (response) => {
                                line.tyro_status = response;
                            },
                            transactionCompleteCallback: (response) =>
                                this.onTransactionComplete(response, resolve),
                        }
                    );
                });
            } else {
                return new Promise((resolve) => {
                    this.tyroClient.initiatePurchase(
                        {
                            amount: Math.round(line.amount * 100).toString(10),
                            mid: this.payment_method_id.tyro_merchant_id,
                            tid: this.payment_method_id.tyro_terminal_id,
                            integrationKey: this.payment_method_id.tyro_integration_key,
                            integratedReceipt: this.payment_method_id.tyro_integrated_receipts,
                            enableSurcharge: true,
                        },
                        {
                            receiptCallback: this.onMerchantReceiptReceived.bind(this),
                            questionCallback: (question, answerCallback) =>
                                this.dialog.add(QuestionDialog, {
                                    question,
                                    answerCallback,
                                }),
                            statusMessageCallback: (response) => {
                                line.tyro_status = response;
                            },
                            transactionCompleteCallback: (response) =>
                                this.onTransactionComplete(response, resolve),
                        }
                    );
                });
            }
        } catch (error) {
            this._showError(error.message);
            return false;
        }
    }

    async send_payment_cancel(order, uuid) {
        /**
         * Override
         */
        super.send_payment_cancel(...arguments);

        try {
            this.tyroClient.cancelCurrentTransaction();
        } catch (error) {
            this._showError(error.message);
            return false;
        }
    }

    _showError(msg, title) {
        if (!title) {
            title = "Tyro Error";
        }
        this.dialog.add(AlertDialog, {
            title: title,
            body: msg,
        });
    }
}
