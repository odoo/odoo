import { registry } from "@web/core/registry";
import { BelowTopFixedElements } from "@website/interactions/below_top_fixed_elements";

export class FaqHorizontal extends BelowTopFixedElements {
    static selector = ".s_faq_horizontal";
    dynamicContent = {
        ...this.dynamicContent,
        _stickyEl: {
            ...this.dynamicContent._stickyEl,
            // Titles saved before the removal of `transition-base` from the
            // template still have it. Its `top` transition would make them lag
            // behind the header (the class is restored when the interaction
            // stops, so the saved content is not altered).
            "t-att-class": () => ({ "transition-base": false }),
        },
    };
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
