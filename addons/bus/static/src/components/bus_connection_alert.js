import { Component, useState } from "@odoo/owl";
import { CONNECTION_STATUS } from "@bus/services/bus_monitoring_service";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

/**
 * @typedef {Object} Props
 * @extends {Component<Props, Env>}
 */
export class BusConnectionAlert extends Component {
    static template = "bus.BusConnectionAlert";
    static props = {};

    setup() {
        this.busMonitoring = useState(useService("bus.monitoring_service"));
        this.CONNECTION_STATUS = CONNECTION_STATUS;
    }

    /**
     * Determine if a border should be shown around the screen in addition to
     * the failure message when an issue is detected.
     */
    get showBorderOnFailure() {
        return false;
    }
}

registry.category("main_components").add("bus.connection_alert", { Component: BusConnectionAlert });
