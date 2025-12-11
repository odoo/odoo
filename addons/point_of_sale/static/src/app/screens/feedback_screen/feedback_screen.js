import { registry } from "@web/core/registry";
import { Component, useRef, onMounted, useEffect, useState, onWillUnmount } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { PriceFormatter } from "@point_of_sale/app/components/price_formatter/price_formatter";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { useErrorHandlers } from "@point_of_sale/app/hooks/hooks";
import { useRouterParamsChecker } from "@point_of_sale/app/hooks/pos_router_hook";
import { PrintPopup } from "@point_of_sale/app/components/popups/print_popup/print_popup";
import { SendReceiptPopup } from "@point_of_sale/app/components/popups/send_receipt_popup/send_receipt_popup";

export class FeedbackScreen extends Component {
    static template = "point_of_sale.FeedbackScreen";
    static storeOnOrder = false;
    static components = { PriceFormatter };
    static props = {
        orderUuid: String,
        waitFor: { type: Object, optional: true },
    };

    setup() {
        super.setup();
        this.pos = usePos();
        useRouterParamsChecker();
        useErrorHandlers();
        this.notification = useService("notification");
        this.ui = useService("ui");
        this.dialog = useService("dialog");
        this.containerRef = useRef("feedback-screen");
        this.amountRef = useRef("amount");
        this.state = useState({
            loading: true,
            timeout: false,
        });

        onMounted(() => {
            this.scaleText();
        });

        useEffect(
            () => {
                const waiter = async () => {
                    try {
                        if (this.props.waitFor) {
                            await this.props.waitFor;
                        }
                    } finally {
                        this.state.loading = false;
                        if (this.isAutoSkip && !this.ignoreTimeout) {
                            this.state.timeout = setTimeout(() => {
                                this.pos.orderDone(this.currentOrder);
                            }, this.pos.feedbackScreenAutoSkipDelay);
                        }
                    }
                };

                waiter();
            },
            () => []
        );

        onWillUnmount(() => {
            clearTimeout(this.state.timeout);
        });
    }

    get isAutoSkip() {
        return (
            this.pos.config.iface_print_auto && this.currentOrder.payment_ids[0]?.payment_method_id
        );
    }

    scaleText() {
        const containerWidth = this.containerRef.el.offsetWidth * 0.8; // 80% of the container width to have some space on the sides
        const textWidth = this.amountRef.el.scrollWidth;

        const scale = Math.min(1, containerWidth / textWidth);
        this.amountRef.el.style.transform = `scale(${scale})`;
    }

    get currentOrder() {
        return this.pos.models["pos.order"].getBy("uuid", this.props.orderUuid);
    }

    onClick(buttonClicked = false) {
        if (!this.isAutoSkip || buttonClicked) {
            if (this.state.loading) {
                this.notification.add(
                    _t("A request is still being processed in the background. Please wait."),
                    {
                        type: "warning",
                    }
                );
                return;
            }
            this.goNext();
        } else {
            this.stopAutomaticSkip();
        }
    }

    stopAutomaticSkip() {
        if (!this.isAutoSkip) {
            return;
        }
        if (this.state.timeout) {
            clearTimeout(this.state.timeout);
            this.state.timeout = false;
        } else {
            this.ignoreTimeout = true;
        }
    }

    goNext() {
        this.pos.orderDone(this.currentOrder);
    }

    get canSendReceipt() {
        return true;
    }

    get canPrintReceipt() {
        return true;
    }

    get canEditPayment() {
        return !this.pos.config.iface_print_auto && this.currentOrder.nb_print === 0;
    }

    clickPrint() {
        this.stopAutomaticSkip();
        this.dialog.add(PrintPopup, {
            order: this.currentOrder,
        });
    }

    clickSend() {
        this.stopAutomaticSkip();
        if (this.canSendReceipt) {
            this.dialog.add(SendReceiptPopup, {
                order: this.currentOrder,
            });
        }
    }

    clickEditPayment() {
        this.stopAutomaticSkip();
        this.pos.orderDetails(this.currentOrder);
    }
}

registry.category("pos_pages").add("FeedbackScreen", {
    name: "FeedbackScreen",
    component: FeedbackScreen,
    route: `/pos/ui/${odoo.pos_config_id}/resume/{string:orderUuid}`,
    params: {},
});
