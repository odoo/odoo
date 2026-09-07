import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

export class StickBelowHeader extends Interaction {
    dynamicSelectors = {
        _stickyEl: () => this.stickyEl || this.el,
    };
    dynamicContent = {
        _stickyEl: {
            "t-att-style": () => ({
                top: `${this.offset}px`,
                maxHeight: `calc(100vh - ${this.offset + 40}px)`,
            }),
        },
    };

    setup() {
        this.stickyEl = undefined;
        this.defaultOffset = 16; // Add 1rem equivalent in px to provide a visual gap by default
        this.offset = this.defaultOffset;
    }

    start() {
        this.updatePosition();
        this.registerCleanup(
            this.services.website_menus.registerCallback(this.updatePosition.bind(this))
        );
    }

    updatePosition() {
        let offset = this.defaultOffset;
        for (const el of this.el.ownerDocument.querySelectorAll(".o_top_fixed_element")) {
            offset += el.getBoundingClientRect().bottom;
        }
        this.offset = offset;
        this.updateContent();
    }
}

registry.category("public.interactions.edit").add("website.sticky_top_to_header", {
    Interaction: StickBelowHeader,
    isAbstract: true,
});
