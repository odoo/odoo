import { Component, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

/**
 * @typedef {Object} Props
 * @extends {Component<Props, Env>}
 */
export class BusConnectionAlert extends Component {
    static template = "mail.BusConnectionAlert";
    static props = {};

    setup() {
        this.busMonitoring = useState(useService("bus.monitoring_service"));
        this.store = useState(useService("mail.store"));
    }
}

registry.category("main_components").add("bus.connection_alert", { Component: BusConnectionAlert });
