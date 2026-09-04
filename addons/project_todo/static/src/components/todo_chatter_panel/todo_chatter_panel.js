import { Chatter } from "@mail/chatter/web_portal_project/chatter";
import { Component, proxy, signal } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { ANIMATION_DURATION, useAnimationMark } from "@web/core/utils/animation";
import { useBus, useService } from "@web/core/utils/hooks";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";

export class TodoChatterPanel extends Component {
    static template = "project_todo.TodoChatterPanel";
    static components = { Chatter };
    static props = {
        ...standardWidgetProps,
    };

    rootRef = signal.ref();

    setup() {
        this.uiService = useService("ui");
        this.state = proxy({
            displayChatter: this.uiService.isSmall,
        });
        // The panel grows in as it appears, and appearing alone is not the cue:
        // it is also opened on mount, from a past session or for a small screen,
        // and it has not been toggled then.
        this.justToggledChatter = useAnimationMark(ANIMATION_DURATION.mount);
        useBus(this.env.bus, "TODO:TOGGLE_CHATTER", this.toggleChatter.bind(this));
    }

    toggleChatter(ev) {
        this.state.displayChatter = ev.detail.displayChatter;
        // Only on the way in: closing the panel takes it away, and there is
        // nothing appearing to acknowledge.
        if (ev.detail.displayChatter && ev.detail.isUserToggle) {
            this.justToggledChatter.mark();
        }
        this.rootRef()?.parentElement?.classList.toggle("d-none", !this.state.displayChatter);
    }
}

export const todoChatterPanel = {
    component: TodoChatterPanel,
    additionalClasses: ["o_todo_chatter", "d-none", "position-relative", "p-0", "overflow-y-auto"],
};

registry.category("view_widgets").add("todo_chatter_panel", todoChatterPanel);
