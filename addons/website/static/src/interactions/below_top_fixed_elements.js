import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

/**
 * Keeps element(s), typically sticky ones, below the elements fixed at the top
 * of the page (e.g. the header), which can move or change size. The covered
 * height is given by the `website_menus` service.
 *
 * What is applied is reverted when the interaction stops, so it can be used on
 * content saved with the page.
 */
export class BelowTopFixedElements extends Interaction {
    dynamicSelectors = {
        ...this.dynamicSelectors,
        _stickyEl: () => this.stickyEl,
    };
    dynamicContent = {
        _stickyEl: {
            "t-att-style": () => {
                // Updated on each frame of the animations of the top fixed
                // elements: a CSS transition on `top` would make the element
                // lag behind them.
                const top = this.topFixedOffset + this.gap;
                const style = { top: `${top}px` };
                if (this.maxHeightGap !== undefined) {
                    style["max-height"] = `calc(100vh - ${top + this.maxHeightGap}px)`;
                }
                return style;
            },
        },
    };

    /**
     * Gap (in px) between the top fixed elements and the element(s).
     */
    gap = 16;
    /**
     * If set, the max-height of the element(s) is limited to the viewport
     * height minus their top and this gap (in px).
     *
     * @type {number|undefined}
     */
    maxHeightGap = undefined;

    setup() {
        /**
         * Element(s) to keep below the top fixed elements. Can be overridden
         * in `setup` by an element, a NodeList, or a falsy value.
         *
         * @type {HTMLElement|NodeList|null}
         */
        this.stickyEl = this.el;
        this.topFixedOffset = this.services.website_menus.getTopFixedOffset();
    }

    start() {
        const update = (topFixedOffset) => {
            if (this.topFixedOffset !== topFixedOffset) {
                this.topFixedOffset = topFixedOffset;
                this.updateContent();
            }
        };
        this.registerCleanup(this.services.website_menus.registerCallback(update));
        // The top fixed elements (e.g. the header) may have notified their
        // changes between the setup and the start of this interaction.
        update(this.services.website_menus.getTopFixedOffset());
    }
}

registry.category("public.interactions.edit").add("website.below_top_fixed_elements", {
    Interaction: BelowTopFixedElements,
    isAbstract: true,
});
