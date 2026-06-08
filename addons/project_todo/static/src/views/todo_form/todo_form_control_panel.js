import { useEffect, onMounted } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { router } from "@web/core/browser/router";
import { ControlPanel } from "@web/search/control_panel/control_panel";

export class TodoFormControlPanel extends ControlPanel {
    static template = "project_todo.TodoFormControlPanel";

    setup() {
        super.setup();
        useEffect(() => {
            if (this.env.isSmall && !this.embeddedPanelState.displayChatter) {
                this.toggleChatter();
            }
        });
        onMounted(() => {
            // We check if we have come from activity view using router action stack and toggle chatter
            const isFromActivityView =
                router.current.actionStack?.[router.current.actionStack?.length - 1]?.view_type ===
                "activity";
            if (
                !this.env.isSmall &&
                !this.embeddedPanelState.displayChatter &&
                (isFromActivityView || JSON.parse(browser.localStorage.getItem("isChatterOpened")))
            ) {
                this.toggleChatter();
            }
        });
    }

    toggleChatter(ev) {
        this.embeddedPanelState.displayChatter = !this.embeddedPanelState.displayChatter;
        if (ev) {
            browser.localStorage.setItem("isChatterOpened", this.embeddedPanelState.displayChatter);
        }
        this.env.bus.trigger("TODO:TOGGLE_CHATTER", {
            displayChatter: this.embeddedPanelState.displayChatter,
        });
    }
}
