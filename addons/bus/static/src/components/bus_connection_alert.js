import { Component } from "@odoo/owl";
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
        this.busMonitoring = useService("bus.monitoring_service");
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
