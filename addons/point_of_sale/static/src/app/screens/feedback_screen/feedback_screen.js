import { Component, onMounted, onWillStart, onWillUnmount, signal } from "@odoo/owl";
import { FeedbackPaymentSummary } from "@point_of_sale/app/components/feedback_payment_summary/feedback_payment_summary";
import { PrintPopup } from "@point_of_sale/app/components/popups/print_popup/print_popup";
import { SendReceiptPopup } from "@point_of_sale/app/components/popups/send_receipt_popup/send_receipt_popup";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { useRouterParamsChecker } from "@point_of_sale/app/hooks/pos_router_hook";
import OrderPaymentValidation from "@point_of_sale/app/utils/order_payment_validation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class FeedbackScreen extends Component {
    static template = "point_of_sale.FeedbackScreen";
    static storeOnOrder = false;
    static components = { FeedbackPaymentSummary };
    static props = {
        orderUuid: String,
        waitFor: { type: Object, optional: true },
    };

    loading = signal(true);
    timeout = signal(null);

    setup() {
        this.pos = usePos();
        this.ui = useService("ui");
        this.dialog = useService("dialog");
        if (new URLSearchParams(window.location.search).get("post_validate") == 1) {
            // This means we got here from a backend redirect, so waitFor is always undefined
            this.waitFor = Promise.withResolvers();
            onMounted(async () => {
                try {
                    const validation = new OrderPaymentValidation({
                        pos: this.pos,
                        orderUuid: this.props.orderUuid,
                    });
                    await validation.afterOrderValidation();
                } finally {
                    this.waitFor.resolve();
                }
            });
        }

        useRouterParamsChecker(this.constructor.name);
        onWillStart(() => {
            this.waiter();
        });

        onWillUnmount(() => {
            clearTimeout(this.timeout());
        });
    }

    async waiter() {
        try {
            if (this.props.waitFor) {
                await this.props.waitFor;
            }
        } finally {
            await this._afterWaitFinished();
        }
    }

    async _afterWaitFinished() {
        this.loading.set(false);

        if (this.isAutoSkip && !this.ignoreTimeout) {
            this.timeout.set(
                setTimeout(() => {
                    this.pos.orderDone(this.currentOrder);
                }, this.pos.feedbackScreenAutoSkipDelay)
            );
        }
    }

    get isAutoSkip() {
        return this.pos.config.autoPrint && this.currentOrder.payment_ids[0]?.payment_method_id;
    }

    get currentOrder() {
        return this.pos.models["pos.order"].getBy("uuid", this.props.orderUuid);
    }

    onClick(buttonClicked = false) {
        if (!this.isAutoSkip || buttonClicked) {
            if (this.loading()) {
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
        if (this.timeout()) {
            clearTimeout(this.timeout());
            this.timeout.set(null);
        } else {
            this.ignoreTimeout = true;
        }
    }

    goNext() {
        this.pos.orderDone(this.currentOrder);
    }

    get canPrintReceipt() {
        return true;
    }

    clickPrint() {
        this.stopAutomaticSkip();
        this.dialog.add(PrintPopup, {
            order: this.currentOrder,
        });
    }

    clickSend() {
        this.stopAutomaticSkip();
        if (this.pos.canSendReceipt) {
            this.dialog.add(SendReceiptPopup, {
                order: this.currentOrder,
            });
        }
    }

    clickEditPayment() {
        this.stopAutomaticSkip();
        this.pos.editPayment(this.currentOrder);
    }
}

registry.category("pos_pages").add("FeedbackScreen", {
    name: "FeedbackScreen",
    component: FeedbackScreen,
    route: `/pos/ui/${odoo.pos_config_id}/resume/{string:orderUuid}`,
    params: {},
});
