import { useService } from "@web/core/utils/hooks";
import { user } from "@web/core/user";
import { Component, onWillStart, useState } from "@odoo/owl";

export class FleetActionHelper extends Component {
    static template = "fleet.FleetActionHelper";
    static props = ["noContentHelp"];
    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.state = useState({
            hasDemoData: false,
        });
        onWillStart(async () => {
            this.state.hasDemoData = await this.orm.call("fleet.vehicle", "has_demo_data", []);
            this.isFleetManager = await user.hasGroup("fleet.fleet_group_manager");
        });
    }

    loadFleetScenario() {
        this.actionService.doAction("fleet.action_load_demo_data");
    }

}
