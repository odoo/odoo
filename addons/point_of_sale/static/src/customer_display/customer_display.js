import { Component, useEffect, whenReady, useRef } from "@odoo/owl";
import { OdooLogo } from "@point_of_sale/app/components/odoo_logo/odoo_logo";
import { MainComponentsContainer } from "@web/core/main_components_container";
import { session } from "@web/session";
import { useService } from "@web/core/utils/hooks";
import { mountComponent } from "@web/env";
import { BadgeTag } from "@web/core/tags_list/badge_tag";
import { useTime } from "@point_of_sale/app/hooks/time_hook";

export class CustomerDisplay extends Component {
    static template = "point_of_sale.CustomerDisplay";
    static components = { OdooLogo, MainComponentsContainer, BadgeTag };
    static props = [];

    setup() {
        this.session = session;
        this.dialog = useService("dialog");
        this.order = useService("customer_display_data");
        this.time = useTime();

        this.scrollableRef = useRef("scrollable");
        useEffect(() => {
            this.scrollableRef.el
                ?.querySelector(".orderline.selected")
                ?.scrollIntoView({ behavior: "smooth", block: "start" });
        });
    }

    get qrPaymentData() {
        return {
            ...this.order.qrPaymentData,
            ...this.order.onlinePaymentData,
        };
    }

    getInternalNotes() {
        return JSON.parse(this.line.internalNote || "[]");
    }
}

whenReady(() => mountComponent(CustomerDisplay, document.body));
