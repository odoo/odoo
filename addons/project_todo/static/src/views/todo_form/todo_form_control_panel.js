import { useEffect } from "@odoo/owl";
import { ControlPanel } from "@web/search/control_panel/control_panel";

export class TodoFormControlPanel extends ControlPanel {
    static template = "project_todo.TodoFormControlPanel";

    setup() {
        super.setup();
        useEffect(
            (isSmall) => {
                if (isSmall && !this.state.displayChatter) {
                    this.toggleChatter();
                }
            },
            () => [this.env.isSmall]
        );
    }

    toggleChatter() {
        this.state.displayChatter = !this.state.displayChatter;
        this.env.bus.trigger("TODO:TOGGLE_CHATTER", { displayChatter: this.state.displayChatter });
    }
}
