import { Component, onWillDestroy, Plugin, usePlugin } from "@odoo/owl";
import { DebugModePlugin } from "@web/core/debug_mode_plugin";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { registry } from "@web/core/registry";
import { services } from "@web/core/services";
import { ProfilingPlugin } from "@web/webclient/debug/profiling/profiling_plugin";

export class ProfilingItem extends Component {
    static components = { DropdownItem };
    static template = "web.DebugMenu.ProfilingItem";
    setup() {
        this.profiling = usePlugin(ProfilingPlugin);
    }

    changeParam(param, ev) {
        this.profiling.setParam(param, ev.target.value);
    }
    toggleParam(param) {
        const value = this.profiling.params()[param];
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

export class ProfilingItemPlugin extends Plugin {
    /** @private */
    debugMode = usePlugin(DebugModePlugin);

    setup() {
        if (!this.debugMode.isActive()) {
            return;
        }
        const debugRegistry = registry.category("debug").category("default");
        debugRegistry.add("profilingItem", () => ({
            type: "component",
            Component: ProfilingItem,
            sequence: 570,
            section: "tools",
        }));
        onWillDestroy(() => debugRegistry.remove("profilingItem"));
    }
}

services.add(ProfilingItemPlugin);
