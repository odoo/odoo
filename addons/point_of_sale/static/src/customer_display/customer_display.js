/** @odoo-module native */
import { Component, useEffect, useRef, whenReady } from "@odoo/owl";
import { OdooLogo } from "@point_of_sale/app/components/odoo_logo/odoo_logo";
import { useSingleDialog } from "@point_of_sale/customer_display/utils";
import { TagsList } from "@web/components/tags_list";
import { makeLogger } from "@web/core/debug/debug_logger";
import { useLifecycleLog } from "@web/core/debug/logger_hooks";
import { useService } from "@web/core/utils/hooks";
import { mountComponent } from "@web/env";
import { session } from "@web/session";
import { MainComponentsContainer } from "@web/ui/main_components_container";

import { CustomerFacingQR } from "./customer_facing_qr.js";
const log = makeLogger("pos.customer_display");

export class CustomerDisplay extends Component {
    static template = "point_of_sale.CustomerDisplay";
    static components = { OdooLogo, MainComponentsContainer, TagsList };
    static props = [];

    setup() {
        useLifecycleLog(log);
        this.session = session;
        this.dialog = useService("dialog");
        this.order = useService("customer_display_data");
        const singleDialog = useSingleDialog();

        this.scrollableRef = useRef("scrollable");
        useEffect(() => {
            this.scrollableRef.el
                ?.querySelector(".orderline.selected")
                ?.scrollIntoView({ behavior: "smooth", block: "start" });
        });

        useEffect(
            (qrPaymentData) => {
                log.logic("qrPaymentData changed", () => ({
                    show: Boolean(qrPaymentData),
                    amount: qrPaymentData?.amount,
                }));
                if (qrPaymentData) {
                    singleDialog.open(CustomerFacingQR, qrPaymentData);
                } else {
                    singleDialog.close();
                }
            },
            () => [this.order.qrPaymentData],
        );
    }

    getInternalNotes(line) {
        return JSON.parse(line.internalNote || "[]");
    }
}

whenReady(() => {
    log.lifecycle("mount", () => ({
        proxy: Boolean(session.proxy_ip),
        device: session.device_uuid,
    }));
    return mountComponent(CustomerDisplay, document.body);
});
