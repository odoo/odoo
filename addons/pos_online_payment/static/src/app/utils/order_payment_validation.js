import OrderPaymentValidation from "@point_of_sale/app/utils/order_payment_validation";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { ask } from "@point_of_sale/app/utils/make_awaitable_dialog";

patch(OrderPaymentValidation.prototype, {
    //@override
    async isOrderValid(isForceValidate) {
        if (!(await super.isOrderValid(...arguments))) {
            return false;
        }

        if (!this.payment_methods_from_config.some((pm) => pm.type === "online")) {
            return true;
        }

        if (this.order.state === "done") {
            this.afterOrderValidation(false);
            return false;
        }

        if (!this.order.isSynced) {
            return true;
        }

        // The server finalizes the order once its online payments cover the total
        const orderServerOPData = await this.pos.updateOnlinePaymentsDataWithServer(this.order, 0);
        if (!orderServerOPData) {
            return ask(this.pos.dialog, {
                title: _t("Online payment unavailable"),
                body: _t(
                    "There is a problem with the server. The order online payment status cannot be retrieved. Are you sure there is no online payment for this order ?"
                ),
                confirmLabel: _t("Yes"),
            });
        }
        if (orderServerOPData.isPaid) {
            await this.afterPaidOrderSavedOnServer(orderServerOPData.paid_order);
            return false; // Cancel normal flow because the current order is already saved on the server.
        }
        if (orderServerOPData.modified_payment_lines) {
            this.pos.dialog.add(AlertDialog, {
                title: _t("Updated online payments"),
                body: _t("There are online payments that were missing in your view."),
            });
            return false;
        }

        return true;
    },
    async afterPaidOrderSavedOnServer(orderJSON) {
        if (!orderJSON) {
            this.pos.dialog.add(AlertDialog, {
                title: _t("Server error"),
                body: _t("The saved order could not be retrieved."),
                showReloadButton: true,
            });
            return;
        }

        // Update the local order with the data from the server, because it's the server
        // that is responsible for saving the final state of an order when there is an
        // online payment in it.
        // This prevents the case where the cashier changes the payment lines after the
        // order is paid with an online payment and the server saves the order as paid.
        // Without that update, the payment lines printed on the receipt ticket would
        // be invalid.
        const isInvoiceRequested = this.order.isToInvoice();
        if (!orderJSON[0] || this.order.id !== orderJSON[0].id) {
            this.pos.dialog.add(AlertDialog, {
                title: _t("Order saving issue"),
                body: _t("The order has not been saved correctly on the server."),
                showReloadButton: true,
            });
            return;
        }
        this.order.state = "paid";
        this.pos.validated_orders_name_server_id_map[this.order.name] = this.order.id;

        // Now, do practically the normal flow
        if ((this.order.isPaidWithCash() || this.order.change) && this.pos.canOpenCashdrawer) {
            this.pos.openCashbox();
        }

        if (isInvoiceRequested) {
            if (!orderJSON[0].account_move) {
                this.pos.dialog.add(AlertDialog, {
                    title: _t("Invoice could not be generated"),
                    body: _t("The invoice could not be generated."),
                    showReloadButton: true,
                });
            } else {
                await this.pos.env.services.account_move.downloadPdf(orderJSON[0].account_move);
            }
        }

        await this.postPushOrderResolve([this.order.id]);

        await this.afterOrderValidation(true);
        const nextPage = this.nextPage;
        this.pos.navigate(nextPage.page, nextPage.params);
    },
});
