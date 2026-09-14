/** @odoo-module native */
import { makeLogger } from "@web/core/debug/debug_logger";
import { serializeDateTime } from "@web/core/l10n/dates";
import { luxon } from "@web/core/l10n/luxon";
import { ConnectionLostError, RPCError } from "@web/core/network";
import { _t } from "@web/core/translation";
import { AlertDialog, ConfirmationDialog } from "@web/ui/dialog";

import { handleRPCError, showLimitedFunctionalityWarning } from "./error_handlers.js";
import { ask } from "./make_awaitable_dialog.js";
import { logPosMessage } from "./pretty_console_log.js";
const log = makeLogger("pos.payment.validation");

/**
 * @param {Object} params
 * @param {Object} params.pos
 * @param {Object} params.order
 * @param {Object} [params.fastPaymentMethod=null]
 */
export default class OrderPaymentValidation {
    constructor({ pos, orderUuid, fastPaymentMethod = null }) {
        this.setup({ pos, orderUuid, fastPaymentMethod });
    }

    setup(vals) {
        this.pos = vals.pos;
        this.orderUuid = vals.orderUuid;
        this.payment_methods_from_config = this.pos.config.orderedPaymentMethods;
        this.fastPaymentLine = null;
        if (vals.fastPaymentMethod) {
            const res = this.order.addPaymentline(vals.fastPaymentMethod);
            this.fastPaymentLine = res?.data || null;
        }
        log.lifecycle("setup", () => ({
            order: this.orderUuid,
            fastPaymentMethod: vals.fastPaymentMethod?.id,
            fastPaymentLine: this.fastPaymentLine?.uuid,
        }));
    }

    rollbackFastPayment() {
        const line = this.fastPaymentLine;
        log.logic("rollbackFastPayment", () => ({
            order: this.orderUuid,
            line: line?.uuid,
            present: Boolean(line && this.order.payment_ids.includes(line)),
        }));
        if (line && this.order.payment_ids.includes(line)) {
            this.order.removePaymentline(line);
        }
        this.fastPaymentLine = null;
    }

    get order() {
        return this.pos.models["pos.order"].getBy("uuid", this.orderUuid);
    }

    get nextPage() {
        if (
            this.pos.config.iface_print_auto &&
            this.pos.config.iface_print_skip_screen
        ) {
            return {
                page: "FeedbackScreen",
                params: {
                    orderUuid: this.order.uuid,
                },
            };
        }

        return {
            page: "ReceiptScreen",
            params: {
                orderUuid: this.order.uuid,
            },
        };
    }

    get paymentLines() {
        return this.order.payment_ids;
    }

    shouldRemoveZeroPayment(line) {
        return (
            line.amount === 0 &&
            !(this.pos.config.hasCashRounding && line.payment_method_id.is_cash_count)
        );
    }

    async beforePostPushOrderResolve(order, order_server_ids) {
        return true;
    }

    shouldDownloadInvoice() {
        if (!this.pos.config.canInvoice) {
            return false;
        }
        return true;
    }

    async shouldHideValidationBehindFeedbackScreen() {
        const nextPage = this.nextPage;
        log.pipeline("finalize: next page", () => ({
            order: this.orderUuid,
            page: nextPage.page,
            background: nextPage.page === "FeedbackScreen",
        }));
        if (nextPage.page === "FeedbackScreen") {
            const waitForFn = async () => {
                try {
                    const response = await this.finalizeValidation();
                    return {
                        ok: !(response instanceof RPCError) && response !== false,
                    };
                } catch (error) {
                    logPosMessage(
                        "OrderPaymentValidation",
                        "shouldHideValidationBehindFeedbackScreen",
                        "Background finalization failed",
                        undefined,
                        [error],
                    );
                    return { ok: false, error };
                }
            };
            nextPage.params.waitFor = waitForFn();
        } else {
            try {
                this.pos.env.services.ui.block();
                const response = await this.finalizeValidation();
                if (response instanceof RPCError || response === false) {
                    return false;
                }
            } finally {
                this.pos.env.services.ui.unblock();
            }
        }

        this.pos.navigate(nextPage.page, nextPage.params);
        return true;
    }

    async validateOrder(isForceValidate) {
        const endValidate = log.perf("validateOrder");
        log.pipeline("validateOrder", () => ({
            order: this.orderUuid,
            isForceValidate,
            state: this.order.state,
            lines: this.order.lines.length,
            payments: this.paymentLines.length,
            toInvoice: this.order.isToInvoice(),
        }));
        const rollbackFastPayment = () => this.rollbackFastPayment();
        if ((await this.askBeforeValidation()) === false) {
            log.logic("validateOrder: askBeforeValidation refused", () => ({
                order: this.orderUuid,
            }));
            rollbackFastPayment();
            endValidate({ order: this.orderUuid, stoppedAt: "askBeforeValidation" });
            return false;
        }
        if ((await this._askForCustomerIfRequired()) === false) {
            rollbackFastPayment();
            endValidate({ order: this.orderUuid, stoppedAt: "customerRequired" });
            return false;
        }
        this.pos.numberBuffer.capture();
        if (!this.checkCashRoundingHasBeenWellApplied()) {
            rollbackFastPayment();
            endValidate({ order: this.orderUuid, stoppedAt: "cashRounding" });
            return false;
        }
        const linesToRemove = this.order.lines.filter((line) => line.canBeRemoved);
        log.logic("validateOrder: zero-qty lines", () => ({
            order: this.orderUuid,
            removed: linesToRemove.map((l) => l.uuid),
        }));
        for (const line of linesToRemove) {
            this.order.removeOrderline(line);
        }
        if (await this.isOrderValid(isForceValidate)) {
            const toRemove = [];
            for (const line of this.paymentLines) {
                if (!line.isDone() || this.shouldRemoveZeroPayment(line)) {
                    toRemove.push(line);
                }
            }
            log.logic("validateOrder: dropping payment lines", () => ({
                order: this.orderUuid,
                removed: toRemove.map((l) => ({
                    payment: l.uuid,
                    status: l.getPaymentStatus(),
                    amount: l.amount,
                })),
            }));

            for (const line of toRemove) {
                this.order.removePaymentline(line);
            }

            const result = await this.shouldHideValidationBehindFeedbackScreen();
            endValidate({ order: this.orderUuid, result });
            return result;
        }

        rollbackFastPayment();
        endValidate({ order: this.orderUuid, stoppedAt: "isOrderValid" });
        return false;
    }

    async finalizeValidation() {
        const endFinalize = log.perf("finalizeValidation");
        log.pipeline("finalizeValidation", () => ({
            order: this.orderUuid,
            openCashbox: Boolean(this.order.isPaidWithCash() || this.order.change),
            payments: this.paymentLines.map((p) => ({
                payment: p.uuid,
                method: p.payment_method_id.id,
                amount: p.amount,
            })),
            toInvoice: this.order.isToInvoice(),
        }));
        if (this.order.isPaidWithCash() || this.order.change) {
            this.pos.hardwareProxy.openCashbox();
        }

        this.order.date_order = serializeDateTime(luxon.DateTime.now());
        for (const line of this.paymentLines) {
            if (this.shouldRemoveZeroPayment(line)) {
                this.order.removePaymentline(line);
            }
        }

        this.pos.addPendingOrder([this.order.id]);
        log.lifecycle("finalizeValidation: state -> paid", () => ({
            order: this.orderUuid,
            id: this.order.id,
        }));
        this.order.state = "paid";
        this.pos.data.localUnsyncedPaidOrderUuids.add(this.order.uuid);

        try {
            const syncOrderResult = await this.pos.syncAllOrders({
                orders: [this.order],
                throw: true,
                force: true,
            });
            if (!syncOrderResult) {
                endFinalize({ order: this.orderUuid, synced: false });
                return false;
            }

            if (this.shouldDownloadInvoice() && this.order.isToInvoice()) {
                log.logic("finalizeValidation: invoice", () => ({
                    order: this.orderUuid,
                    accountMove: this.order.raw.account_move,
                }));
                if (this.order.raw.account_move) {
                    await this.pos.env.services.account_move.downloadPdf(
                        this.order.raw.account_move,
                    );
                } else {
                    this.pos.dialog.add(AlertDialog, {
                        title: _t("Backend Invoice"),
                        body: _t(
                            "An error occurred while generating an invoice. You can try again from the order list.",
                        ),
                    });
                }
            }

            const postPushOrders = syncOrderResult.filter((order) =>
                order.waitForPushOrder(),
            );
            log.logic("finalizeValidation: post push", () => ({
                order: this.orderUuid,
                synced: syncOrderResult.length,
                postPush: postPushOrders.map((o) => o.id),
            }));
            if (postPushOrders.length > 0) {
                await this.postPushOrderResolve(
                    postPushOrders.map((order) => order.id),
                );
            }

            const result = await this.afterOrderValidation();
            endFinalize({ order: this.orderUuid, id: this.order.id, synced: true });
            return result;
        } catch (error) {
            endFinalize({ order: this.orderUuid, error: error?.constructor?.name });
            return this.handleValidationError(error);
        }
    }

    async postPushOrderResolve(ordersServerId) {
        const postPushResult = await this.beforePostPushOrderResolve(
            this.order,
            ordersServerId,
        );
        if (!postPushResult) {
            this.pos.dialog.add(AlertDialog, {
                title: _t("Error: no internet connection."),
                body: _t(
                    "Some, if not all, post-processing after syncing order failed.",
                ),
            });
        }
    }

    async afterOrderValidation() {
        log.pipeline("afterOrderValidation", () => ({
            order: this.orderUuid,
            restaurant: this.pos.config.module_pos_restaurant,
            nbPrint: this.order.nb_print,
            printAuto: this.pos.config.iface_print_auto,
            toInvoice: this.order.isToInvoice(),
            finalized: this.order.finalized,
        }));
        if (!this.pos.config.module_pos_restaurant) {
            this.pos
                .checkPreparationStateAndSentOrderInPreparation(this.order, {
                    orderDone: true,
                })
                .catch((error) => {
                    logPosMessage(
                        "OrderPaymentValidation",
                        "afterOrderValidation",
                        "Failed to send the order to preparation tools",
                        undefined,
                        [error],
                    );
                });
        }

        if (this.order.nb_print === 0 && this.pos.config.iface_print_auto) {
            const invoiced_finalized = this.order.isToInvoice()
                ? this.order.finalized
                : true;
            if (invoiced_finalized) {
                await this.pos.printReceipt({ order: this.order });
            }
        }
        this.pos.env.services.pos_stock.refresh();
    }

    async askBeforeValidation() {
        return true;
    }

    handleValidationError(error) {
        log.logic("handleValidationError", () => ({
            order: this.orderUuid,
            connectionLost: error instanceof ConnectionLostError,
            rpcError: error instanceof RPCError,
            error: error?.message,
        }));
        if (error instanceof ConnectionLostError) {
            this.pos.data.syncLocalDataInIndexedDB();
            this.afterOrderValidation();
            showLimitedFunctionalityWarning(this.pos);
            return error;
        } else if (error instanceof RPCError) {
            this.order.state = "draft";
            handleRPCError(error, this.pos.dialog);
        } else {
            throw error;
        }
        return error;
    }

    checkCashRoundingHasBeenWellApplied() {
        const useRound = this.pos.config.hasCashRounding;
        if (!useRound) {
            return true;
        }

        const cashRounding = this.pos.config.rounding_method;
        const order = this.order;
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
            log.logic("checkCashRounding: mismatch", () => ({
                order: this.orderUuid,
                payment: payment.uuid,
                amountPaid,
                expectedAmountPaid,
            }));

            this.pos.dialog.add(AlertDialog, {
                title: _t("Rounding error in payment lines"),
                body: _t(
                    "The amount of your payment lines must be rounded to validate the transaction.\n" +
                        "The rounding precision is %(rounding)s so you should set %(expectedAmount)s as payment amount instead of %(paidAmount)s.",
                    {
                        rounding: cashRounding.rounding.toFixed(
                            this.pos.currency.decimal_places,
                        ),
                        expectedAmount: expectedAmountPaid.toFixed(
                            this.pos.currency.decimal_places,
                        ),
                        paidAmount: amountPaid.toFixed(
                            this.pos.currency.decimal_places,
                        ),
                    },
                ),
            });
            return false;
        }
        return true;
    }

    async isOrderValid(isForceValidate) {
        const reject = (reason, extra) => {
            log.logic("isOrderValid: rejected", () => ({
                order: this.orderUuid,
                reason,
                ...(extra || {}),
            }));
            return false;
        };
        if (this.order.isRefundInProcess()) {
            return reject("refundInProcess");
        }

        const inFlightPayment = this.order.payment_ids.find(
            (p) =>
                p.isElectronic() &&
                !p.isDone() &&
                !["pending", "retry"].includes(p.getPaymentStatus()),
        );
        if (this.pos.paymentTerminalInProgress || inFlightPayment) {
            reject("terminalInProgress", { inFlightPayment: inFlightPayment?.uuid });
            this.pos.dialog.add(AlertDialog, {
                title: _t("Electronic payment in progress"),
                body: _t(
                    "The order cannot be validated while a payment terminal transaction is in progress. Wait for the transaction to finish or cancel it on the payment screen first.",
                ),
            });
            return false;
        }

        if (this.order.getOrderlines().length === 0 && this.order.isToInvoice()) {
            reject("emptyInvoicedOrder");
            this.pos.dialog.add(AlertDialog, {
                title: _t("Empty Order"),
                body: _t(
                    "There must be at least one product in your order before it can be validated and invoiced.",
                ),
            });
            return false;
        }

        if (
            (this.order.isToInvoice() || this.order.getShippingDate()) &&
            !this.order.getPartner()
        ) {
            reject("partnerRequired");
            const confirmed = await ask(this.pos.dialog, {
                title: _t("Please select the Customer"),
                body: _t(
                    "You need to select the customer before you can invoice or ship an order.",
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
            reject("shippingAddress", { partner: partner.id });
            this.pos.dialog.add(AlertDialog, {
                title: _t("Incorrect address for shipping"),
                body: _t("The selected customer needs an address."),
            });
            return false;
        }

        const missingRequirement = this.order.getMissingPresetRequirement();
        if (missingRequirement) {
            const { field, message } = missingRequirement;
            reject("presetRequirement", { field });
            this.pos.dialog.add(AlertDialog, {
                title: field ? _t("%s required", field) : _t("Missing required"),
                body: message || _t("Some required information is missing."),
            });
            return false;
        }

        if (
            !this.pos.currency.isZero(this.order.priceIncl) &&
            this.order.payment_ids.length === 0
        ) {
            this.pos.notification.add(
                _t("Select a payment method to validate the order."),
            );
            return reject("noPayment", { priceIncl: this.order.priceIncl });
        }

        if (!this.order.isPaid()) {
            return reject("notPaid", {
                priceIncl: this.order.priceIncl,
                amountPaid: this.order.amountPaid,
                remainingDue: this.order.remainingDue,
            });
        }

        if (
            Math.abs(
                this.order.priceIncl -
                    this.order.amountPaid +
                    this.order.appliedRounding,
            ) > 0.00001
        ) {
            if (!this.pos.models["pos.payment.method"].some((pm) => pm.is_cash_count)) {
                reject("changeWithoutCash", {
                    priceIncl: this.order.priceIncl,
                    amountPaid: this.order.amountPaid,
                });
                this.pos.dialog.add(AlertDialog, {
                    title: _t("Cannot return change without a cash payment method"),
                    body: _t(
                        "There is no cash payment method available in this point of sale to handle the change.\n\n Please pay the exact amount or add a cash payment method in the point of sale configuration",
                    ),
                });
                return false;
            }
        }

        if (
            !isForceValidate &&
            this.order.priceIncl > 0 &&
            this.order.priceIncl * 1000 < this.order.amountPaid
        ) {
            reject("largeAmountConfirmation", {
                priceIncl: this.order.priceIncl,
                amountPaid: this.order.amountPaid,
            });
            this.pos.dialog.add(ConfirmationDialog, {
                title: _t("Please Confirm Large Amount"),
                body:
                    _t("Are you sure that the customer wants to  pay") +
                    " " +
                    this.pos.env.utils.formatCurrency(this.order.amountPaid) +
                    " " +
                    _t("for an order of") +
                    " " +
                    this.pos.env.utils.formatCurrency(this.order.priceIncl) +
                    " " +
                    _t('? Clicking "Confirm" will validate the payment.'),
                confirm: () => this.validateOrder(true),
            });
            return false;
        }

        if (!this.order._isValidEmptyOrder()) {
            return reject("invalidEmptyOrder");
        }

        log.logic("isOrderValid: accepted", () => ({
            order: this.orderUuid,
            isForceValidate,
            priceIncl: this.order.priceIncl,
            amountPaid: this.order.amountPaid,
        }));
        return true;
    }

    async _askForCustomerIfRequired() {
        const splitPayments = this.order.payment_ids.filter(
            (payment) => payment.payment_method_id.split_transactions,
        );
        if (splitPayments.length && !this.order.getPartner()) {
            const paymentMethod = splitPayments[0].payment_method_id;
            log.logic("askForCustomerIfRequired: split payment needs partner", () => ({
                order: this.orderUuid,
                method: paymentMethod.id,
            }));
            const confirmed = await ask(this.pos.dialog, {
                title: _t("Customer Required"),
                body: _t(
                    "Customer is required for %s payment method.",
                    paymentMethod.name,
                ),
            });
            if (confirmed) {
                await this.pos.selectPartner();
            }
            return false;
        }
    }
}
