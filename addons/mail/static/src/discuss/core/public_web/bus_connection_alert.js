import { Component } from "@odoo/owl";
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
        this.busMonitoring = useService("bus.monitoring_service");
        this.store = useService("mail.store");
    }
}

export const connectionAlertService = {
    dependencies: ["bus.monitoring_service", "mail.store"],
    start() {
        registry
            .category("main_components")
<<<<<<< saas-18.2
            .add("bus.ConnectionAlert", { Component: BusConnectionAlert });
||||||| cfc1afbe6ba1ec461d00f391f5f8f64309f249e9
registry.category("main_components").add("bus.connection_alert", { Component: BusConnectionAlert });
=======
            .add("bus.connection_alert", { Component: BusConnectionAlert });
>>>>>>> defc98b989763d79c92c72920efe19ad76a97695
    },
};
registry.category("services").add("bus.connection_alert", connectionAlertService);
