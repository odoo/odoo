import { Chatter } from "@mail/chatter/web_portal/chatter";

import { Component, useState, useRef } from "@odoo/owl";

import { registry } from "@web/core/registry";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";
import { useBus } from "@web/core/utils/hooks";

export class TodoChatterPanel extends Component {
    static template = "project_todo.TodoChatterPanel";
    static components = { Chatter };
    static props = {
        ...standardWidgetProps,
    };

    setup() {
        this.state = useState({
            displayChatter: this.env.isSmall,
        });
        this.rootRef = useRef("root");
        useBus(this.env.bus, "TODO:TOGGLE_CHATTER", this.toggleChatter);
    }

    toggleChatter(ev) {
        this.state.displayChatter = ev.detail.displayChatter;
        this.rootRef.el?.parentElement?.classList.toggle('d-none', !this.state.displayChatter);
    }
}

export const todoChatterPanel = {
    component: TodoChatterPanel,
    additionalClasses: ["o_todo_chatter", "d-none", "position-relative", "p-0", "overflow-y-auto"],
};

registry.category("view_widgets").add("todo_chatter_panel", todoChatterPanel);
