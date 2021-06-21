/** @odoo-module **/

import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { useBus } from "@web/core/bus_hook";
import { useService } from "@web/core/service_hook";

const { Component } = owl;

export class ProfilingItem extends Component {
    setup() {
        this.profiling = useService("profiling");
        this.actionService = useService("action");
        useBus(this.props.bus, "UPDATE", this.render);
    }

    changeParam(param, ev) {
        this.profiling.setParam(param, ev.target.value);
    }
    openProfiles() {
        this.actionService.doAction("base.action_menu_ir_profile");
    }
}
ProfilingItem.components = { DropdownItem };
ProfilingItem.template = "web.DebugMenu.ProfilingItem";
