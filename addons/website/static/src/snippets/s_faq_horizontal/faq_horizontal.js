import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

class FaqHorizontal extends Interaction {
    static selector = ".s_faq_horizontal";

    setup() {
        this.titles = this.el.getElementsByClassName("s_faq_horizontal_entry_title");
        this.registerCleanup(this.services.website_menus.registerCallback(this.updateTitlesPosition.bind(this)));
    }

    start() {
        this.updateTitlesPosition();
    }

    updateTitlesPosition() {
        let position = 16; // Add 1rem equivalent in px to provide a visual gap by default
        for (const el of document.querySelectorAll(".o_top_fixed_element")) {
            position += el.getBoundingClientRect().bottom;
        }

        for (const title of this.titles) {
            title.style.top = `${position}px`;
            title.style.maxHeight = `calc(100vh - ${position + 40}px)`;
        }
    }
}

registry
    .category("public.interactions")
    .add("website.faq_horizontal", FaqHorizontal);

registry
    .category("public.interactions.edit")
    .add("website.faq_horizontal", { Interaction: FaqHorizontal });
