import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

export class StickyBelowHeader extends Interaction {
    dynamicSelectors = {
        ...this.dynamicSelectors,
        _stickyEl: () => this.stickyEl,
    };
    dynamicContent = {
        _stickyEl: {
            "t-att-style": () => {
                // The offset follows the header geometry on each animation
                // frame. Adding a CSS transition to `top` would interpolate
                // every intermediate value and make the sticky element lag
                // behind the header.
                const style = { top: `${this.offset}px` };
                if (this.maxHeightGap !== undefined) {
                    style.maxHeight = `calc(100vh - ${this.offset + this.maxHeightGap}px)`;
                }
                return style;
            },
        },
    };

    defaultOffset = 16;
    maxHeightGap = undefined;

    setup() {
        this.stickyEl = this.el;
        this.offset = this.defaultOffset;
    }

    start() {
        this.updatePosition();
        this.registerCleanup(
            this.services.website_menus.registerCallback(this.updatePosition.bind(this))
        );
    }

    updatePosition() {
        // A hiding header drops `o_top_fixed_element` before its transition is
        // over. Keep measuring it until it reaches its final position.
        const topFixedEls = this.el.ownerDocument.querySelectorAll(
            ".o_top_fixed_element, header.o_transitioning"
        );
        const visibleBottom = Math.max(
            0,
            ...Array.from(topFixedEls, (el) => el.getBoundingClientRect().bottom)
        );
        const offset = this.defaultOffset + visibleBottom;
        if (this.offset !== offset) {
            this.offset = offset;
            this.updateContent();
        }
    }
}

registry.category("public.interactions.edit").add("website.sticky_below_header", {
    Interaction: StickyBelowHeader,
    isAbstract: true,
});
