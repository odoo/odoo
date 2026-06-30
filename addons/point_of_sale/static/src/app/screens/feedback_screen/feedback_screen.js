import { registry } from "@web/core/registry";
import { Component, onWillStart, onWillUnmount, signal, props, t } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { useService } from "@web/core/utils/hooks";
import { useErrorHandlers } from "@point_of_sale/app/hooks/hooks";
import { useRouterParamsChecker } from "@point_of_sale/app/hooks/pos_router_hook";
import { PrintPopup } from "@point_of_sale/app/components/popups/print_popup/print_popup";
import { SendReceiptPopup } from "@point_of_sale/app/components/popups/send_receipt_popup/send_receipt_popup";
import { FeedbackPaymentSummary } from "@point_of_sale/app/components/feedback_payment_summary/feedback_payment_summary";

export class FeedbackScreen extends Component {
    static template = "point_of_sale.FeedbackScreen";
    static storeOnOrder = false;
    static components = { FeedbackPaymentSummary };
    props = props({
        orderUuid: t.string(),
        waitFor: t.object().optional(),
    });

    loading = signal(true);
    timeout = signal(null);

    setup() {
        super.setup();
        this.pos = usePos();
        useRouterParamsChecker();
        useErrorHandlers();
        this.ui = useService("ui");
        this.dialog = useService("dialog");

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
