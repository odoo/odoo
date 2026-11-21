import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

export class Tabs extends Interaction {
    static selector = ".s_tabs_common";

    start() {
        for (const tabEl of this.el.querySelectorAll("[data-bs-toggle='tab'][role='tab'].active")) {
            const bsTab = window.Tab.getOrCreateInstance(tabEl);

            this.registerCleanup(() => {
                bsTab.dispose();
            });
        }
    }
}

registry.category("public.interactions").add("website.tabs", Tabs);
