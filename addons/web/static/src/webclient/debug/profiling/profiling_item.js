import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { useBus, useService } from "@web/core/utils/hooks";

import { Component, EventBus } from "@odoo/owl";

export class ProfilingItem extends Component {
    static components = { DropdownItem };
    static template = "web.DebugMenu.ProfilingItem";
    static props = {
        bus: { type: EventBus },
    };
    setup() {
        this.profiling = useService("profiling");
        useBus(this.props.bus, "UPDATE", this.render);
    }

    changeParam(param, ev) {
        this.profiling.setParam(param, ev.target.value);
    }
    toggleParam(param) {
        const value = this.profiling.state.params.execution_context_qweb;
        this.profiling.setParam(param, !value);
    }
    openProfiles() {
        if (this.env.services.action) {
            // using doAction in the backend to preserve breadcrumbs and stuff
            this.env.services.action.doAction("base.action_menu_ir_profile");
        } else {
            // No action service means we are in the frontend.
            window.location = "/web/#action=base.action_menu_ir_profile";
        }
    }
}
