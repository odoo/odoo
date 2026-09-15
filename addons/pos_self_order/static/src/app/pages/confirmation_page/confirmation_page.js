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
                this.defaultTimeout = setTimeout(() => this.backToHome({ force: true }), 15000);
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

    async initOrder() {
        const order = await this.selfOrder.getOrderByAccessToken(this.props.orderAccessToken);

        if (!order) {
            this.router.navigate("default");
            return;
        }

        this.selfOrder.selectedOrderUuid = order.uuid;

        if (
            this.selfOrder.hasPaymentMethod() &&
            this.selfOrder.config.self_ordering_mode === "mobile" &&
            this.selfOrder.config.self_ordering_pay_after === "each" &&
            order.state !== "paid"
        ) {
            this.router.navigate("default");
            return;
        }

        this.confirmedOrder.uiState.receiptReady = await this.beforePrintOrder();
        this.state.onReload = false;
    }

    canPrintReceipt() {
        return (
            !this.isPrinting &&
            this.confirmedOrder &&
            this.confirmedOrder.uiState.receiptReady &&
            (!this.confirmedOrder.nb_print || this.confirmedOrder.nb_print < 1)
        );
    }

    async beforePrintOrder() {
        // meant to be overriden.
        return true;
    }

    async printOrderChanges() {
        // If mobile self-ordering, the preparation changes are printed with Obox
        // If the kiosk language has changed, the preparation changes are printed after the reload in the kiosk default language
        if (this.selfOrder.config.self_ordering_mode === "mobile" || this.needsLanguageReset()) {
            return;
        }

        const order = this.confirmedOrder;
        await this.selfOrder.ticketPrinter.printOrderChanges({ order, webFallback: false });
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
                            this.backToHome();
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

    backToHome({ force = false } = {}) {
        if (!force && (!this.confirmedOrder?.uiState?.receiptReady || this.state.onReload)) {
            return;
        }

        if (this.selfOrder.config.self_ordering_mode !== "kiosk") {
            this.router.navigate("default");
            return;
        }

        this.state.onReload = true;

        if (this.needsLanguageReset()) {
            // Print later (after reload) so the prep ticket will print in Kiosk lang
            this.selfOrder.setPendingPreparation(this.props.orderAccessToken);
            cookie.set("frontend_lang", this.defaultLanguage.code);
        }

        // A full page load, to refresh the kiosk data and to apply the restored language.
        this.router.load("default");
    }

    get defaultLanguage() {
        return this.selfOrder.config.self_ordering_default_language_id;
    }

    needsLanguageReset() {
        return Boolean(
            this.selfOrder.config.self_ordering_mode === "kiosk" &&
                this.defaultLanguage &&
                this.selfOrder.currentLanguage.code !== this.defaultLanguage.code
        );
    }

    async updateHasPaper(state) {
        await rpc("/pos-self-order/change-printer-status", {
            access_token: this.selfOrder.access_token,
            has_paper: state,
        });
        this.selfOrder.has_paper = state;
    }

    get orderTimeStr() {
        return this.confirmedOrder.preset_time.toFormat("h:mm a");
    }
}
