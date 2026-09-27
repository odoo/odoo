import { Component, onMounted, onPatched, signal, usePlugin } from "@odoo/owl";
import { OdooLogo } from "@point_of_sale/app/components/odoo_logo/odoo_logo";
import { MainComponentsContainer } from "@web/core/main_components_container";
import { session } from "@web/session";
import { useService } from "@web/core/utils/hooks";
import { CustomerDisplayPlugin } from "@point_of_sale/customer_display/customer_display_plugin";
import { BadgeTag } from "@web/core/tags_list/badge_tag";
import { useTime } from "@point_of_sale/app/hooks/time_hook";
import { FeedbackPaymentSummary } from "@point_of_sale/app/components/feedback_payment_summary/feedback_payment_summary";

export class CustomerDisplay extends Component {
    static template = "point_of_sale.CustomerDisplay";
    static components = { OdooLogo, MainComponentsContainer, BadgeTag, FeedbackPaymentSummary };

    scrollableRef = signal.ref();
    customerDisplay = usePlugin(CustomerDisplayPlugin);

    setup() {
        this.session = session;
        this.uiService = useService("ui");
        this.customerDisplay.init({ bus: useService("bus_service") });

        this.time = useTime();

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

    get qrData() {
        return {
            ...this.order.qrData,
            ...this.order.onlinePaymentData,
        };
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
