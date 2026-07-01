import { Component, whenReady, useEffect, Resource } from "@odoo/owl";
import { OdooLogo } from "@point_of_sale/app/components/odoo_logo/odoo_logo";
import { MainComponentsContainer } from "@web/core/main_components_container";
import { session } from "@web/session";
import { useService } from "@web/core/utils/hooks";
import { mountComponent } from "@web/env";
import { BadgeTag } from "@web/core/tags_list/badge_tag";
import { useTime } from "@point_of_sale/app/hooks/time_hook";
import { FeedbackPaymentSummary } from "@point_of_sale/app/components/feedback_payment_summary/feedback_payment_summary";

export class CustomerDisplay extends Component {
    static template = "point_of_sale.CustomerDisplay";
    static components = { OdooLogo, MainComponentsContainer, BadgeTag, FeedbackPaymentSummary };
    static props = [];

    lines = new Resource({ name: "orderlines" });
    setup() {
        this.session = session;
        this.customerDisplayService = useService("customer_display_service");
        this.customerDisplayService.initReceiver();
        this.order = this.customerDisplayService.data;
        window.displayData = this.customerDisplayService;

        this.time = useTime();

        useEffect(() =>
            this.lines
                .items()
                .find((line) => line.dataset.uuid == this.order.selectedLineUuid)
                ?.scrollIntoView({ behavior: "smooth", block: "start" })
        );
    }

    get qrPaymentData() {
        return {
            ...this.order.qrPaymentData,
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

whenReady(() => mountComponent(CustomerDisplay, document.body));
