import { Component, onMounted, onWillUnmount, proxy, t, useProps } from "@odoo/owl";
import { PrintingFailurePopup } from "@pos_self_order/app/components/printing_failure_popup/printing_failure_popup";
import { useSelfOrder } from "@pos_self_order/app/services/self_order_service";
import { cookie } from "@web/core/browser/cookie";
import { rpc } from "@web/core/network/rpc";
import { useService } from "@web/core/utils/hooks";
import { imageDataUri } from "@point_of_sale/utils";

export class ConfirmationPage extends Component {
    static template = "pos_self_order.ConfirmationPage";
    props = useProps({ orderAccessToken: t.string(), screenMode: t.string() });

    setup() {
        this.selfOrder = useSelfOrder();
        this.router = useService("router");
        this.dialog = useService("dialog");
        this.changeToDisplay = [];
        this.state = proxy({
            continueDisabled: true,
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

        onWillUnmount(() => {
            clearTimeout(this.defaultTimeout);
        });

        onMounted(async () => {
            await this.initOrder();
            // Init the order before trying to print anything
            try {
                await this.printOrder();
                if (!this.selfOrder.hasPaymentMethod() || this.confirmedOrder.state === "paid") {
                    await this.printOrderChanges();
                }
            } finally {
                this.state.continueDisabled = false;
            }
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
        this.state.onReload = false;
    }

    canPrintReceipt() {
        return (
            !this.isPrinting &&
            this.confirmedOrder &&
            (!this.confirmedOrder.nb_print || this.confirmedOrder.nb_print < 1)
        );
    }

    /**
     * The ticket is printed from the changes computed when the order was sent
     * (see `sendDraftOrderToServer`): the server creates the preparation lines on its
     * side, so there is no quantity difference left to compute here. They are consumed
     * before printing, so that the ticket cannot be printed twice.
     */
    async printOrderChanges() {
        if (this.selfOrder.config.self_ordering_mode === "mobile") {
            return;
        }

        const order = this.confirmedOrder;
        const orderChange = order?.uiState.preparationChanges;

        if (!orderChange) {
            return;
        }
        delete order.uiState.preparationChanges;
        this.selfOrder.data.debouncedSynchronizeLocalDataInIndexedDB();
        await this.selfOrder.ticketPrinter.printOrderChanges({
            order,
            opts: { orderChange },
            printers: this.selfOrder.ticketPrinter.localPreparationPrinters,
        });
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
                if (order.state === "paid") {
                    order.nb_print = 1;
                    if (order.isSynced && result) {
                        await rpc("/pos_self_order/kiosk/increment_nb_print/", {
                            access_token: this.selfOrder.access_token,
                            order_id: order.id,
                            order_access_token: order.access_token,
                        });
                    }
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
        if (!this.setDefautLanguage()) {
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
    get logoUrl() {
        return this.selfOrder.config.logo
            ? imageDataUri(this.selfOrder.config.logo.content)
            : false;
    }
}
