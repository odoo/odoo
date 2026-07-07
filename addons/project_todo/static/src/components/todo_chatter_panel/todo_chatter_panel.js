import { Chatter } from "@mail/chatter/web_portal_project/chatter";
import { Component, proxy, signal } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useBus, useService } from "@web/core/utils/hooks";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";

export class TodoChatterPanel extends Component {
    static template = "project_todo.TodoChatterPanel";
    static components = { Chatter };
    static props = {
        ...standardWidgetProps,
    };

    rootRef = signal(null);

    setup() {
        this.uiService = useService("ui");
        this.state = proxy({
            displayChatter: this.uiService.isSmall,
        });
        useBus(this.env.bus, "TODO:TOGGLE_CHATTER", this.toggleChatter);
    }

    toggleChatter(ev) {
        this.state.displayChatter = ev.detail.displayChatter;
        this.rootRef()?.parentElement?.classList.toggle("d-none", !this.state.displayChatter);
    }
}

export const todoChatterPanel = {
    component: TodoChatterPanel,
    additionalClasses: ["o_todo_chatter", "d-none", "position-relative", "p-0", "overflow-y-auto"],
};

registry.category("view_widgets").add("todo_chatter_panel", todoChatterPanel);
