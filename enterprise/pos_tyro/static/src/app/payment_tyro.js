/* global TYRO */

import { loadJS } from "@web/core/assets";
import { PaymentInterface } from "@point_of_sale/app/payment/payment_interface";
import { register_payment_method } from "@point_of_sale/app/store/pos_store";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { TYRO_LIB_URLS } from "@pos_tyro/urls";
import { FailureDialog } from "@pos_tyro/app/components/failure_dialog";
import { QuestionDialog } from "@pos_tyro/app/components/question_dialog";

export class PaymentTyro extends PaymentInterface {
    setup() {
        super.setup(...arguments);
        this.dialog = this.env.services.dialog;
        this.orm = this.env.services.orm;
        this.currentQuestion = null;
        this.loadTyroClient();
    }

    get fast_payments() {
        return false;
    }

    async loadTyroClient() {
        await loadJS(TYRO_LIB_URLS[this.payment_method_id.tyro_mode]);
        const posProductInfo = await this.orm.call("pos.payment.method", "get_tyro_product_info", [
            this.payment_method_id.id,
        ]);
        this.tyroClient = new TYRO.IClient(posProductInfo.apiKey, posProductInfo);

        if (
            this.paymentLine?.payment_method_id === this.payment_method_id &&
            ["waitingCard", "waitingCancel"].includes(this.paymentLine.payment_status)
        ) {
            this.resumePayment();
        }
    }

    get paymentLine() {
        return this.pos.get_order()?.get_selected_paymentline();
    }

    addTip(tip) {
        const tipAmount = parseInt(tip, 10) / 100;
        if (!this.pos.config.tip_product_id) {
            this.pos.add_tyro_surcharge(
                tipAmount,
                this.payment_method_id.tyro_surcharge_product_id
            );
            this._showError(
                "A tip was added on the Tyro terminal, but tipping is not enabled for this Point of Sale. It will instead be recorded as a surcharge.",
                "Tyro Warning"
            );
        } else {
            const tipProduct = this.pos.config.tip_product_id;
            const orderLines = this.pos.get_order().lines;
            const existingTip = orderLines.find((line) => line.product_id.id === tipProduct.id);
            this.pos.set_tip(tipAmount + (existingTip?.price_unit ?? 0));
        }
        this.paymentLine.set_amount(this.paymentLine.amount + tipAmount);
    }

    addSurcharge(surcharge) {
        const surchargeAmount = parseFloat(surcharge);
        this.pos.add_tyro_surcharge(
            surchargeAmount,
            this.payment_method_id.tyro_surcharge_product_id
        );
        this.paymentLine.set_amount(this.paymentLine.amount + surchargeAmount);
    }

    onTransactionComplete(response, resultCallback) {
        const line = this.paymentLine;
        this.dialog.closeAll();
        this.currentQuestion = null;

        if (response.customerReceipt) {
            line.set_receipt_info(response.customerReceipt);
        }

        if (response.result === "APPROVED") {
            line.transaction_id = response.transactionId;
            line.payment_ref_no = response.transactionReference;
            line.payment_method_authcode = response.authorisationCode;
            line.card_type = response.cardType;
            line.card_no = response.elidedPan;
            if (response.tipAmount) {
                this.addTip(response.tipAmount);
            }
            if (response.surchargeAmount && response.surchargeAmount !== "0.00") {
                this.addSurcharge(response.surchargeAmount);
            }
            resultCallback(true);
        } else {
            if (response.result !== "CANCELLED" || response.customerReceipt) {
                this.dialog.add(FailureDialog, {
                    result: response.result,
                    hasReceipt: !!response.customerReceipt,
                    printReceipt: () => this.pos.printReceipt({ printBillActionTriggered: true }),
                });
            }
            resultCallback(false);
        }
        this.printMerchantReceipt();
    }

    onMerchantReceiptReceived(response) {
        if (
            response.signatureRequired ||
            this.payment_method_id.tyro_always_print_merchant_receipt
        ) {
            this.paymentLine.tyroMerchantReceipt = response.merchantReceipt;
            if (response.signatureRequired) {
                this.printMerchantReceipt();
            }
        }
    }

    printMerchantReceipt() {
        if (this.paymentLine.tyroMerchantReceipt) {
            this.pos
                .printReceipt({
                    printBillActionTriggered: true,
                })
                .then(() => {
                    this.paymentLine.tyroMerchantReceipt = null;
                });
        }
    }

    onQuestionReceived(question, answerCallback) {
        // Tyro re-sends the question every so often, so
        // we do nothing if we are already displaying the
        // question.
        if (this.currentQuestion === question.text) {
            return;
        }
        this.currentQuestion = question.text;
        const onClickAnswer = (answer) => {
            this.currentQuestion = null;
            answerCallback(answer);
        };
        this.dialog.add(QuestionDialog, {
            question,
            onClickAnswer,
        });
    }

    validateRefundAmount() {
        const order = this.pos.get_order();
        const totalAmount = order.getTotalDue();
        const amountDue = order.get_due();
        const line = order.get_selected_paymentline();
        if (totalAmount < 0 && amountDue > line.amount) {
            this._showError("You cannot refund more than the original amount.");
            return false;
        }
        return true;
    }

    resumePayment() {
        const line = this.paymentLine;
        const resolve = (success) => {
            if (success) {
                line.set_payment_status("done");
            } else {
                line.set_payment_status("retry");
            }
        };
        const requestCallbacks = {
            receiptCallback: this.onMerchantReceiptReceived.bind(this),
            questionCallback: this.onQuestionReceived.bind(this),
            statusMessageCallback: (response) => {
                line.tyro_status = response;
            },
            transactionCompleteCallback: (response) =>
                this.onTransactionComplete(response, resolve),
        };
        if (line.payment_status === "waitingCancel") {
            line.set_payment_status("waitingCard");
        }
        this.tyroClient.continueLastTransaction(requestCallbacks);
    }

    async send_payment_request(uuid) {
        /**
         * Override
         */
        await super.send_payment_request(...arguments);
        const line = this.paymentLine;
        try {
            line.set_payment_status("waitingCard");
            line.tyro_status = "Initiating...";

            return new Promise((resolve) => {
                const requestArguments = {
                    amount: Math.abs(Math.round(line.amount * 100)).toString(10),
                    mid: this.payment_method_id.tyro_merchant_id,
                    tid: this.payment_method_id.tyro_terminal_id,
                    integrationKey: this.payment_method_id.tyro_integration_key,
                    integratedReceipt: this.payment_method_id.tyro_integrated_receipts,
                };
                const requestCallbacks = {
                    receiptCallback: this.onMerchantReceiptReceived.bind(this),
                    questionCallback: this.onQuestionReceived.bind(this),
                    statusMessageCallback: (response) => {
                        line.tyro_status = response;
                    },
                    transactionCompleteCallback: (response) =>
                        this.onTransactionComplete(response, resolve),
                };

                if (line.amount < 0) {
                    if (this.validateRefundAmount()) {
                        this.tyroClient.initiateRefund(requestArguments, requestCallbacks);
                    } else {
                        resolve(false);
                    }
                } else {
                    this.tyroClient.initiatePurchase(
                        { ...requestArguments, enableSurcharge: true },
                        requestCallbacks
                    );
                }
            });
        } catch (error) {
            this._showError(error.message);
            return false;
        }
    }

    async send_payment_cancel(order, uuid) {
        /**
         * Override
         */
        await super.send_payment_cancel(...arguments);

        try {
            this.tyroClient.cancelCurrentTransaction();
        } catch (error) {
            this._showError(error.message);
            return true;
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

register_payment_method("tyro", PaymentTyro);
