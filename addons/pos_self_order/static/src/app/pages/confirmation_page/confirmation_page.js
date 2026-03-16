import { useLayoutEffect, useState } from "@web/owl2/utils";
import { Component, onMounted, onWillUnmount } from "@odoo/owl";
import { useSelfOrder } from "@pos_self_order/app/services/self_order_service";
import { cookie } from "@web/core/browser/cookie";
import { useService } from "@web/core/utils/hooks";
import { rpc } from "@web/core/network/rpc";
import { PrintingFailurePopup } from "@pos_self_order/app/components/printing_failure_popup/printing_failure_popup";

export class ConfirmationPage extends Component {
    static template = "pos_self_order.ConfirmationPage";
    static props = ["orderAccessToken", "screenMode"];

    setup() {
        this.selfOrder = useSelfOrder();
        this.router = useService("router");
        this.dialog = useService("dialog");
        this.changeToDisplay = [];
        this.state = useState({
            onReload: true,
            payment: this.props.screenMode === "pay",
        });

        onMounted(() => {
            if (this.selfOrder.config.self_ordering_mode === "kiosk") {
                this.defaultTimeout = setTimeout(() => {
                    this.router.navigate("default");
                }, 30000);
            }
        });
        useLayoutEffect(
            () => {
                if (
                    !this.confirmedOrder ||
                    !this.confirmedOrder.uiState?.receiptReady ||
                    typeof this.confirmedOrder.id !== "number"
                ) {
                    return;
                }

                const printReceipts = async () => {
                    await this.printOrder();
                    await this.printOrderChanges();
                };

                printReceipts();
            },
            () => [this.confirmedOrder?.uiState?.receiptReady]
        );
        onWillUnmount(() => {
            clearTimeout(this.defaultTimeout);
        });

        onMounted(async () => {
            await this.initOrder();
        });
    }

    get confirmedOrder() {
        return this.selfOrder.models["pos.order"].getBy("uuid", this.selfOrder.selectedOrderUuid);
    }

    async initOrder(retry = true) {
        const order = this.selfOrder.models["pos.order"].find(
            (o) => o.access_token === this.props.orderAccessToken
        );

        if (!order && retry) {
            await this.selfOrder.getUserDataFromServer([this.props.orderAccessToken]);
            return this.initOrder(false);
        }

        this.selfOrder.selectedOrderUuid = order.uuid;

        if (
            !order ||
            (this.selfOrder.hasPaymentMethod() &&
                this.selfOrder.config.self_ordering_mode === "mobile" &&
                this.selfOrder.config.self_ordering_pay_after === "each" &&
                order.state !== "paid")
        ) {
            this.router.navigate("default");
            return;
        }

        this.selfOrder.selectedOrderUuid = order.uuid;
        this.confirmedOrder.uiState.receiptReady = this.beforePrintOrder();
        this.state.onReload = false;
    }

    canPrintReceipt() {
        return (
            !this.isPrinting &&
            this.confirmedOrder.uiState.receiptReady &&
            (!this.confirmedOrder.nb_print || this.confirmedOrder.nb_print < 1)
        );
    }

    beforePrintOrder() {
        // meant to be overriden.
        return true;
    }

    /**
     * Two call are performed to update-last-changes.
     *
     * The first one is to get the last changes from the server and to
     * be sure that the customer doesn't already try to order something
     * to the kitchen.
     *
     * The second one is to update the last changes with the current
     * status of the order. Since this application is public, we cannot
     * fully trust the client data, and we need the server to validate
     * the changes before sending them to the printer.
     */
    async printOrderChanges() {
        const order = this.confirmedOrder;
        if (!order) {
            return;
        }

        if (this.selfOrder.config.self_ordering_mode === "mobile") {
            const result = await rpc("/pos-self-order/update-last-changes", {
                access_token: this.selfOrder.access_token,
                order_id: order.id,
                order_access_token: order.access_token,
            });
            this.selfOrder.models.connectNewData(result);
        }

        // Preparation display part ensure changes are up to date.
        await this.selfOrder.ticketPrinter.printOrderChanges({ order, webFallback: false });
        const result = await rpc("/pos-self-order/update-last-changes", {
            access_token: this.selfOrder.access_token,
            order_id: order.id,
            order_access_token: order.access_token,
            update: true,
        });
        this.selfOrder.models.connectNewData(result);
        this.selfOrder.data.debouncedSynchronizeLocalDataInIndexedDB();
    }

    async printOrder() {
        if (this.selfOrder.config.self_ordering_mode === "kiosk" && this.canPrintReceipt()) {
            try {
                this.isPrinting = true;
                const order = this.confirmedOrder;
                const result = await this.selfOrder.ticketPrinter.printOrderReceipt({
                    order,
                    webFallback: false,
                });

                if (!this.selfOrder.has_paper) {
                    this.updateHasPaper(true);
                }
                order.nb_print = 1;
                if (order.isSynced && result) {
                    await rpc("/pos_self_order/kiosk/increment_nb_print/", {
                        access_token: this.selfOrder.access_token,
                        order_id: order.id,
                        order_access_token: order.access_token,
                    });
                }
            } catch (e) {
                if (["EPTR_REC_EMPTY", "EPTR_COVER_OPEN"].includes(e.errorCode)) {
                    this.dialog.add(PrintingFailurePopup, {
                        trackingNumber: this.confirmedOrder.tracking_number,
                        message: e.body,
                        close: () => {
                            this.router.navigate("default");
                        },
                    });
                    this.updateHasPaper(false);
                } else {
                    console.error(e);
                }
            } finally {
                this.isPrinting = false;
            }
        }
    }

    get printOptions() {
        return {};
    }

    backToHome() {
        if (this.confirmedOrder.uiState.receiptReady && !this.setDefautLanguage()) {
            this.router.navigate("default");
        }
    }

    async updateHasPaper(state) {
        await rpc("/pos-self-order/change-printer-status", {
            access_token: this.selfOrder.access_token,
            has_paper: state,
        });
        this.selfOrder.has_paper = state;
    }

    setDefautLanguage() {
        const defaultLanguage = this.selfOrder.config.self_ordering_default_language_id;

        if (
            defaultLanguage &&
            this.selfOrder.currentLanguage.code !== defaultLanguage.code &&
            !this.state.onReload &&
            this.selfOrder.config.self_ordering_mode === "kiosk"
        ) {
            cookie.set("frontend_lang", defaultLanguage.code);
            window.location.reload();
            this.state.onReload = true;
            return true;
        }

        return this.state.onReload;
    }
    get orderTimeStr() {
        return this.confirmedOrder.preset_time.toFormat("h:mm a");
    }
}
