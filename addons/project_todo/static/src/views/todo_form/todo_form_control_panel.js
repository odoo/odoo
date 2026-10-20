import { useEffect, onMounted, signal } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { router } from "@web/core/browser/router";
import { ControlPanel } from "@web/search/control_panel/control_panel";

export class TodoFormControlPanel extends ControlPanel {
    static template = "project_todo.TodoFormControlPanel";

    setup() {
        super.setup();
        this.displayChatter = signal(false);
        useEffect(() => {
            if (this.uiService.isSmall && !this.displayChatter()) {
                this.toggleChatter();
            }
        });
        onMounted(() => {
            // We check if we have come from activity view using router action stack and toggle chatter
            const isFromActivityView =
                router.current.actionStack?.[router.current.actionStack?.length - 1]?.view_type ===
                "activity";
            if (
                !this.uiService.isSmall &&
                !this.displayChatter() &&
                (isFromActivityView || JSON.parse(browser.localStorage.getItem("isChatterOpened")))
            ) {
                this.toggleChatter();
            }
        });
    }

    toggleChatter(ev) {
        this.displayChatter.set(!this.displayChatter());
        if (ev) {
            browser.localStorage.setItem("isChatterOpened", this.displayChatter());
        }
        this.env.bus.trigger("TODO:TOGGLE_CHATTER", {
            displayChatter: this.displayChatter(),
        });
    }
}
