/* eslint-disable no-console */
/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, useState } from "@odoo/owl";

/**
 * AI Job Status Widget — live extraction state on the invoice form.
 *
 * Subscribes to the `invoice_agent` bus.bus channel and renders the latest
 * extraction state (queued → extracting → ready) without a page refresh.
 * The backend publishes each transition through `bus.bus._sendone`; this
 * widget only listens.
 */
export class AIStatusWidget extends Component {
    static template = "invoice_agent.ai_status_widget";

    static props = {
        record: Object,
        fieldInfo: { type: Object, optional: true },
        readonly: { type: Boolean, optional: true },
    };

    setup() {
        this.orm = useService("orm");
        this.busService = useService("bus_service");
        this.state = useState({
            liveStatus: this.props.record?.data?.ai_job_uuid ? "queued" : "",
        });
        this.busService.addChannel("invoice_agent");
        this._busHandle = this.busService.subscribe(
            "invoice_agent",
            this._onBusNotification.bind(this)
        );
    }

    _onBusNotification(notification) {
        const moveId = this.props.record?.resId;
        if (!moveId || notification?.move_id !== moveId) {
            return; // another invoice's status — ignore
        }
        const status = notification?.status;
        if (["queued", "extracting", "ready", "failed"].includes(status)) {
            this.state.liveStatus = status;
        }
    }

    get label() {
        const labels = {
            queued: "Queued",
            extracting: "Extracting…",
            ready: "Ready",
            failed: "Failed",
        };
        return labels[this.state.liveStatus] || "—";
    }

    get decorationClass() {
        const classes = {
            queued: "text-secondary",
            extracting: "text-info",
            ready: "text-success",
            failed: "text-danger",
        };
        return classes[this.state.liveStatus] || "";
    }

    get iconClass() {
        if (this.state.liveStatus === "extracting") {
            return "fa-solid fa-spinner fa-spin";
        }
        if (this.state.liveStatus === "ready") {
            return "fa-solid fa-circle-check";
        }
        if (this.state.liveStatus === "failed") {
            return "fa-solid fa-circle-xmark";
        }
        return "fa-solid fa-clock";
    }
}

export const aiStatusWidget = {
    component: AIStatusWidget,
    supportedTypes: ["char"],
};

registry.category("fields").add("ai_status_widget", aiStatusWidget);
