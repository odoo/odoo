import { onMounted, useEffect } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { router } from "@web/core/browser/router";
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
        onMounted(() => {
            // We check if we have come from activity view using router action stack and toggle chatter
            const isFromActivityView =
                router.current.actionStack?.[router.current.actionStack?.length - 1]?.view_type ===
                "activity";
            if (
                !this.env.isSmall &&
                !this.state.displayChatter &&
                (isFromActivityView || JSON.parse(browser.localStorage.getItem("isChatterOpened")))
            ) {
                this.toggleChatter();
            }
        });
    }

    toggleChatter(ev) {
        this.state.displayChatter = !this.state.displayChatter;
        if (ev) {
            browser.localStorage.setItem("isChatterOpened", this.state.displayChatter);
        }
        this.env.bus.trigger("TODO:TOGGLE_CHATTER", { displayChatter: this.state.displayChatter });
    }
}
