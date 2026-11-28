import { Component, onMounted, onPatched, signal, untrack, useEffect, usePlugin } from "@odoo/owl";
import { OdooLogo } from "@point_of_sale/app/components/odoo_logo/odoo_logo";
import { MainComponentsContainer } from "@web/core/main_components_container";
import { session } from "@web/session";
import { useService } from "@web/core/utils/hooks";
import { CustomerDisplayPlugin } from "@point_of_sale/customer_display/customer_display_plugin";
import { BadgeTag } from "@web/core/tags_list/badge_tag";
import { useTime } from "@point_of_sale/app/hooks/time_hook";
import { FeedbackPaymentSummary } from "@point_of_sale/app/components/feedback_payment_summary/feedback_payment_summary";
import { _t } from "@web/core/l10n/translation";
import { debounce } from "@web/core/utils/timing";
import {
    TipSelector,
    confirmLargeTip,
} from "@point_of_sale/app/components/tip_selector/tip_selector";

export class CustomerDisplay extends Component {
    static template = "point_of_sale.CustomerDisplay";
    static components = {
        OdooLogo,
        MainComponentsContainer,
        BadgeTag,
        FeedbackPaymentSummary,
        TipSelector,
    };

    scrollableRef = signal.ref();
    customerDisplay = usePlugin(CustomerDisplayPlugin);
    tipInputDraft = signal(null);

    setup() {
        this.session = session;
        this.uiService = useService("ui");
        this.dialog = useService("dialog");
        this.customerDisplay.init({ bus: useService("bus_service") });

        this.time = useTime();

        this.sendTipInput = debounce(
            (orderUuid, amount) =>
                this.customerDisplay.sendAction("tip", { orderUuid, action: "input", amount }),
            300
        );

        // A tipInputDraft belongs to the tip screen of one order: drop it, and its pending
        // send, when that screen closes or changes order (e.g. the cashier settles
        // while the customer is typing).
        let draftOrderUuid;
        useEffect(() => {
            const orderUuid = this.tipScreen?.orderUuid;
            if (orderUuid === draftOrderUuid) {
                return;
            }
            draftOrderUuid = orderUuid;
            untrack(() => {
                this.sendTipInput.cancel();
                this.tipInputDraft.set(null);
            });
        });

        useEffect(() => {
            const confirmation = this.tipScreen?.confirmation;
            untrack(() => this.syncTipConfirmationDialog(confirmation));
        });

        onMounted(() => this.scrollSelectedIntoView());
        onPatched(() => this.scrollSelectedIntoView());
    }

    scrollSelectedIntoView() {
        this.scrollableRef()
            ?.querySelector(".orderline.selected")
            ?.scrollIntoView({ behavior: "smooth", block: "start" });
    }

    get order() {
        return this.customerDisplay.data();
    }

    get posWelcomeMessage() {
        return this.session.welcome_message || _t("Welcome");
    }

    get qrData() {
        return {
            ...this.order.qrData,
            ...this.order.onlinePaymentData,
        };
    }

    get tipScreen() {
        return this.order.tipScreen;
    }

    get tipInputValue() {
        return this.tipInputDraft() ?? this.tipScreen.inputTipAmount;
    }

    onTipInput(value) {
        this.tipInputDraft.set(value);
        this.sendTipInput(this.tipScreen.orderUuid, value);
    }

    get tipSelectedPercentage() {
        return this.tipInputDraft() === null ? this.tipScreen.selectedPercentage || "" : "";
    }

    syncTipConfirmationDialog(confirmation) {
        if (!confirmation) {
            // Settled, cancelled or taken over from the terminal.
            this.closeTipConfirmationDialog?.();
            return;
        }
        if (this.closeTipConfirmationDialog) {
            return;
        }
        const confirmed = confirmLargeTip(this.dialog, confirmation);
        this.closeTipConfirmationDialog = confirmed.close;
        confirmed.then((isConfirmed) => {
            this.closeTipConfirmationDialog = null;
            // Nothing to answer when the terminal already dropped the confirmation.
            if (this.tipScreen?.confirmation) {
                this.onTipAction(isConfirmed ? "confirm" : "cancel_confirm");
            }
        });
    }

    onTipAction(action, values = {}) {
        const draft = this.tipInputDraft();
        this.sendTipInput.cancel();
        this.tipInputDraft.set(null);
        if (action === "settle" && draft !== null) {
            // The last typed amount may still be waiting in the 300 ms delay: send it with the settle.
            values = { ...values, amount: draft };
        }
        this.customerDisplay.sendAction("tip", {
            orderUuid: this.tipScreen.orderUuid,
            action,
            ...values,
        });
    }

    parseInternalNotes(noteStr) {
        if (!noteStr || typeof noteStr !== "string") {
            return [];
        }
        return JSON.parse(noteStr);
    }

    get configLogoSrc() {
        return `/web/image/pos.config/${this.session.config_id}/logo`;
    }
}
