import { AlertDialog, ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { serializeDateTime } from "@web/core/l10n/dates";
import { _t } from "@web/core/l10n/translation";
import { ConnectionLostError, RPCError } from "@web/core/network/rpc";
import { handleRPCError } from "./error_handlers";
import { ask } from "./make_awaitable_dialog";

/**
 * This class contains all methods related to order validation. Previously,
 * these methods were only used on the payment screen, but now that we have quick
 * order validation, they are used in different places.
 *
 * All behaviors related to order validation must be found in this class.
 *
 * @param {Object} params - The parameters for the order validation.
 * @param {Object} params.pos - The pos_store instance.
 * @param {Object} params.order - The order to validate.
 * @param {Object} [params.fastPaymentMethod=null] - The payment method to use for fast payment validation.
 */
export default class OrderPaymentValidation {
    constructor({ pos, order, fastPaymentMethod = null }) {
        this.pos = pos;
        this.order = order;

        if (fastPaymentMethod) {
            this.order.addPaymentline(fastPaymentMethod);
        }
    }

    get nextPage() {
        return !this.error
            ? {
                  page: "ReceiptScreen",
                  params: {
                      orderUuid: this.order.uuid,
                  },
              }
            : this.pos.defaultPage;
    }

    get paymentLines() {
        return this.order.payment_ids;
    }

    /**
     * This method can be overridden to perform checks before starting the order validation process.
     */
    async askBeforeValidation() {
        return true;
    }

    /**
     * This method can be overridden to perform checks before starting the order validation process.
     */
    async beforePostPushOrderResolve(order, order_server_ids) {
        return true;
    }

    /**
     * This method can be overridden to perform checks before starting the order validation process.
     */
    shouldDownloadInvoice() {
        return true;
    }

    async validateOrder(isForceValidate) {
        if (!this.pos.isFastPaymentRunning && (await this.askBeforeValidation()) === false) {
            return false;
        }
        this.pos.numberBuffer.capture();
        if (!this.checkCashRoundingHasBeenWellApplied()) {
            return false;
        }
        const linesToRemove = this.order.lines.filter((line) => line.canBeRemoved);
        for (const line of linesToRemove) {
            this.order.removeOrderline(line);
        }
        if (await this.isOrderValid(isForceValidate)) {
            // remove pending payments before finalizing the validation
            const toRemove = [];
            for (const line of this.paymentLines) {
                if (!line.isDone() || line.amount === 0) {
                    toRemove.push(line);
                }
            }

            for (const line of toRemove) {
                this.order.removePaymentline(line);
            }

            await this.finalizeValidation();
            await this.afterOrderValidation();
        }

        return false;
    }

    async finalizeValidation() {
        if (this.order.isPaidWithCash() || this.order.getChange()) {
            this.pos.hardwareProxy.openCashbox();
        }

        this.order.date_order = serializeDateTime(luxon.DateTime.now());
        for (const line of this.paymentLines) {
            if (!line.amount === 0) {
                this.order.removePaymentline(line);
            }
        }

        this.pos.addPendingOrder([this.order.id]);
        this.order.state = "paid";

        if (!this.pos.isFastPaymentRunning) {
            this.pos.env.services.ui.block();
        }
        let syncOrderResult;
        try {
            // 1. Save order to server.
            syncOrderResult = await this.pos.syncAllOrders({ throw: true });
            if (!syncOrderResult) {
                return;
            }

            // 2. Invoice.
            if (this.shouldDownloadInvoice() && this.order.isToInvoice()) {
                if (this.order.raw.account_move) {
                    await this.invoiceService.downloadPdf(this.order.raw.account_move);
                } else {
                    throw {
                        code: 401,
                        message: "Backend Invoice",
                        data: { order: this.order },
                    };
                }
            }
        } catch (error) {
            return this.handleValidationError(error);
        } finally {
            if (!this.pos.isFastPaymentRunning) {
                this.pos.env.services.ui.unblock();
            }
        }

        // 3. Post process.
        const postPushOrders = syncOrderResult.filter((order) => order.waitForPushOrder());
        if (postPushOrders.length > 0) {
            await this.postPushOrderResolve(postPushOrders.map((order) => order.id));
        }

        return !!syncOrderResult && syncOrderResult.length > 0;
    }

    async postPushOrderResolve(ordersServerId) {
        const postPushResult = await this.beforePostPushOrderResolve(this.order, ordersServerId);
        if (!postPushResult) {
            this.pos.dialog.add(AlertDialog, {
                title: _t("Error: no internet connection."),
                body: _t("Some, if not all, post-processing after syncing order failed."),
            });
        }
    }

    async afterOrderValidation() {
        // Always show the next screen regardless of error since pos has to
        // continue working even offline.
        let switchScreen = true;
        let nextPage = this.nextPage;

        if (!this.pos.config.module_pos_restaurant) {
            this.pos.sendOrderInPreparation(this.order, { orderDone: true });
        }

        if (
            nextPage.page === "ReceiptScreen" &&
            this.order.nb_print === 0 &&
            this.pos.config.iface_print_auto
        ) {
            const invoiced_finalized = this.order.isToInvoice() ? this.order.finalized : true;
            if (invoiced_finalized) {
                await this.pos.printReceipt({ order: this.order });

                if (this.pos.config.iface_print_skip_screen) {
                    this.pos.orderDone(this.order);
                    switchScreen = this.order.uuid === this.pos.selectedOrderUuid;
                    nextPage = {
                        page: "FeedbackScreen",
                        params: {
                            orderUuid: this.order.uuid,
                        },
                    };
                    if (switchScreen) {
                        this.selectNextOrder();
                    }
                }
            }
        }

        if (switchScreen) {
            this.pos.navigate(nextPage.page, nextPage.params);
        }
    }

    handleValidationError(error) {
        if (error instanceof ConnectionLostError) {
            this.pos.navigate(this.nextPage.page, this.nextPage.params);
            Promise.reject(error);
        } else if (error instanceof RPCError) {
            this.order.state = "draft";
            handleRPCError(error, this.dialog);
        } else {
            throw error;
        }
        return error;
    }

    checkCashRoundingHasBeenWellApplied() {
        const cashRounding = this.pos.config.rounding_method;
        if (!cashRounding) {
            return true;
        }

        const order = this.pos.getOrder();
        const currency = this.pos.currency;
        for (const payment of order.payment_ids) {
            if (!payment.payment_method_id.is_cash_count) {
                continue;
            }

            const amountPaid = payment.getAmount();
            const expectedAmountPaid = cashRounding.round(amountPaid);
            if (currency.isZero(expectedAmountPaid - amountPaid)) {
                continue;
            }

            this.pos.dialog.add(AlertDialog, {
                title: _t("Rounding error in payment lines"),
                body: _t(
                    "The amount of your payment lines must be rounded to validate the transaction.\n" +
                        "The rounding precision is %(rounding)s so you should set %(expectedAmount)s as payment amount instead of %(paidAmount)s.",
                    {
                        rounding: cashRounding.rounding.toFixed(this.pos.currency.decimal_places),
                        expectedAmount: expectedAmountPaid.toFixed(
                            this.pos.currency.decimal_places
                        ),
                        paidAmount: amountPaid.toFixed(this.pos.currency.decimal_places),
                    }
                ),
            });
            return false;
        }
        return true;
    }

    async isOrderValid(isForceValidate) {
        if (this.order.isRefundInProcess()) {
            return false;
        }

        if (this.order.getOrderlines().length === 0 && this.order.isToInvoice()) {
            this.pos.dialog.add(AlertDialog, {
                title: _t("Empty Order"),
                body: _t(
                    "There must be at least one product in your order before it can be validated and invoiced."
                ),
            });
            return false;
        }

        if ((await this.pos._askForCustomerIfRequired()) === false) {
            return false;
        }

        if (
            (this.order.isToInvoice() || this.order.getShippingDate()) &&
            !this.order.getPartner()
        ) {
            const confirmed = await ask(this.dialog, {
                title: _t("Please select the Customer"),
                body: _t(
                    "You need to select the customer before you can invoice or ship an order."
                ),
            });
            if (confirmed) {
                this.pos.selectPartner();
            }
            return false;
        }

        const partner = this.order.getPartner();
        if (
            this.order.getShippingDate() &&
            !(partner.name && partner.street && partner.city && partner.country_id)
        ) {
            this.pos.dialog.add(AlertDialog, {
                title: _t("Incorrect address for shipping"),
                body: _t("The selected customer needs an address."),
            });
            return false;
        }

        if (!this.order.presetRequirementsFilled) {
            this.pos.dialog.add(AlertDialog, {
                title: _t("Customer required"),
                body: _t("Please add a valid customer to the order."),
            });
            return false;
        }

        if (
            !this.pos.currency.isZero(this.order.getTotalWithTax()) &&
            this.order.payment_ids.length === 0
        ) {
            this.notification.add(_t("Select a payment method to validate the order."));
            return false;
        }

        if (!this.order.isPaid() || this.invoicing) {
            return false;
        }

        // The exact amount must be paid if there is no cash payment method defined.
        if (
            Math.abs(
                this.order.getTotalWithTax() -
                    this.order.getTotalPaid() +
                    this.order.getRoundingApplied()
            ) > 0.00001
        ) {
            if (!this.pos.models["pos.payment.method"].some((pm) => pm.is_cash_count)) {
                this.pos.dialog.add(AlertDialog, {
                    title: _t("Cannot return change without a cash payment method"),
                    body: _t(
                        "There is no cash payment method available in this point of sale to handle the change.\n\n Please pay the exact amount or add a cash payment method in the point of sale configuration"
                    ),
                });
                return false;
            }
        }

        // if the change is too large, it's probably an input error, make the user confirm.
        if (
            !isForceValidate &&
            this.order.getTotalWithTax() > 0 &&
            this.order.getTotalWithTax() * 1000 < this.order.getTotalPaid()
        ) {
            this.pos.dialog.add(ConfirmationDialog, {
                title: _t("Please Confirm Large Amount"),
                body:
                    _t("Are you sure that the customer wants to  pay") +
                    " " +
                    this.env.utils.formatCurrency(this.order.getTotalPaid()) +
                    " " +
                    _t("for an order of") +
                    " " +
                    this.env.utils.formatCurrency(this.order.getTotalWithTax()) +
                    " " +
                    _t('? Clicking "Confirm" will validate the payment.'),
                confirm: () => this.validateOrder(true),
            });
            return false;
        }

        if (!this.order._isValidEmptyOrder()) {
            return false;
        }

        return true;
    }
}
