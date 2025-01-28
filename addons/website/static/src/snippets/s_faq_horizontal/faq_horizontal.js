import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

export class FaqHorizontal extends Interaction {
    static selector = ".s_faq_horizontal";
    dynamicContent = {
        ".s_faq_horizontal_entry_title": {
            "t-att-style": () => ({
                "top": `${this.offset}px`,
                "maxHeight": `calc(100vh - ${this.offset + 40}px)`,
            }),
        },
    };

    setup() {
        this.offset = 16;
    }

    start() {
        this.updateTitlesPosition();
        this.registerCleanup(this.services.website_menus.registerCallback(this.updateTitlesPosition.bind(this)));
    }

    updateTitlesPosition() {
        let offset = 16; // Add 1rem equivalent in px to provide a visual gap by default
        for (const el of this.el.ownerDocument.querySelectorAll(".o_top_fixed_element")) {
            offset += el.getBoundingClientRect().bottom;
        }
        this.offset = offset;
        this.updateContent();
    }
}

registry
    .category("public.interactions")
    .add("website.faq_horizontal", FaqHorizontal);

registry
    .category("public.interactions.edit")
    .add("website.faq_horizontal", {
        Interaction: FaqHorizontal,
    });
