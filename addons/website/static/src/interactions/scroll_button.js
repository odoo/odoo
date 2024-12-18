import { registry } from "@web/core/registry";
import { isVisible } from "@web/core/utils/ui";
import { AnchorSlide } from "@website/interactions/anchor_slide";

export class ScrollButton extends AnchorSlide {
    static selector = ".o_scroll_button";

    animateClick(ev) {
        ev.preventDefault();
        // Scroll to the next visible element after the current one.
        const currentSectionEl = this.el.closest("section");
        let nextEl = currentSectionEl.nextElementSibling;
        while (nextEl) {
            if (isVisible(nextEl)) {
                this.scrollTo(nextEl);
                return;
            }
            nextEl = nextEl.nextElementSibling;
        }
    }
}

registry
    .category("public.interactions")
    .add("website.scroll_button", ScrollButton);
