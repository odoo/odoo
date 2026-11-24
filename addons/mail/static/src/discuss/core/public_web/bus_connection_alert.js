import { Component, Plugin } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { services } from "@web/core/services";
import { useService } from "@web/core/utils/hooks";

export class BusConnectionAlert extends Component {
    static template = "mail.BusConnectionAlert";

    setup() {
        this.busMonitoring = useService("bus.monitoring_service");
        this.store = useService("mail.store");
    }
}

export class BusConnectionAlertPlugin extends Plugin {
    setup() {
        registry
            .category("main_components")
            .add("bus.ConnectionAlert", { Component: BusConnectionAlert });
    }
}
services.add(BusConnectionAlertPlugin);
