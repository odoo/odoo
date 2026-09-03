import { StickBelowHeader } from "@website/interactions/sticky_below_header";
import { registry } from "@web/core/registry";

export class FaqHorizontal extends StickBelowHeader {
    static selector = ".s_faq_horizontal";

    setup() {
        super.setup();
        this.stickyEl = this.el.querySelectorAll(".s_faq_horizontal_entry_title");
    }
}

registry.category("public.interactions").add("website.faq_horizontal", FaqHorizontal);

registry.category("public.interactions.edit").add("website.faq_horizontal", {
    Interaction: FaqHorizontal,
});
