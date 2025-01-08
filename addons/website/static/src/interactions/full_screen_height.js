import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

import { isVisible } from "@web/core/utils/ui";

export class FullScreenHeight extends Interaction {
    static selector = ".o_full_screen_height";
    dynamicContent = {
        _window: {
            "t-on-resize.noupdate": this.debounced(this.updateContent, 250),
        },
        _root: {
            "t-att-style": () => ({
                "min-height": this.isActive ? `${this.computeIdealHeight()}px !important` : undefined,
            }),
        },
    };

    setup() {
        this.inModal = !!this.el.closest(".modal");
        const currentHeight = this.el.getBoundingClientRect().height;
        const idealHeight = this.computeIdealHeight();
        // Only initialize if taller than the ideal height as some extra css
        // rules may alter the full-screen-height class behavior in some
        // cases (blog...).
        this.isActive = !isVisible(this.el) || (currentHeight > idealHeight + 1);
    }

    computeIdealHeight() {
        const windowHeight = window.outerHeight;
        if (this.inModal) {
            return windowHeight;
        }

        // Doing it that way allows to considerer fixed headers, hidden headers,
        // connected users, ...
        const firstContentEl = this.el.ownerDocument.querySelector("#wrapwrap > main > :first-child"); // first child to consider the padding-top of main
        const mainTopPos = firstContentEl.getBoundingClientRect().top + this.el.ownerDocument.documentElement.scrollTop;
        return (windowHeight - mainTopPos);
    }
}

registry
    .category("public.interactions")
    .add("website.full_screen_height", FullScreenHeight);

registry
    .category("public.interactions.edit")
    .add("website.full_screen_height", {
        Interaction: FullScreenHeight,
    });
