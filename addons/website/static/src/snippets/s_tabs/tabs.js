import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

export class TabsEdit extends Interaction {
    static selector = ".s_tabs";
    setup() {
        // Stable fix: add the class in the setup so that it is kept on save.
        // TODO: remove in master (20.0)
        const tabLinkEls = this.el.querySelectorAll(".s_tabs_nav .nav-item .nav-link[role='tab']");
        if (
            tabLinkEls.length &&
            !tabLinkEls[0].classList.contains("oe_unremovable")
        ) {
            for (const tabLinkEl of tabLinkEls) {
                tabLinkEl.classList.add("oe_unremovable");
            }
        }
    }
}

registry.category("public.interactions.edit").add("website.tabs_edit", {
    Interaction: TabsEdit,
});
