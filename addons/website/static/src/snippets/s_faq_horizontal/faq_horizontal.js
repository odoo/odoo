import { registry } from "@web/core/registry";
import { StickyBelowHeader } from "@website/interactions/sticky_below_header";

export class FaqHorizontal extends StickyBelowHeader {
    static selector = ".s_faq_horizontal";
    maxHeightGap = 40;

    setup() {
        super.setup();
        this.stickyEl = this.el.querySelectorAll(".s_faq_horizontal_entry_title");
    }
}

registry.category("public.interactions").add("website.faq_horizontal", FaqHorizontal);

registry.category("public.interactions.edit").add("website.faq_horizontal", {
    Interaction: FaqHorizontal,
});
