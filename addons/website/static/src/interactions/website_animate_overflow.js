import { registry } from "@web/core/registry";
import { Interaction } from "@web/public/interaction";
import { getScrollingElement } from "@web/core/utils/scrolling";

export class WebsiteAnimateOverflow extends Interaction {
    static selector = "#wrapwrap";
    dynamicSelectors = {
        ...this.dynamicSelectors,
        "_scrollingElement": () => this.scrollingElement,
    };
    dynamicContent = {
        "_scrollingElement": {
            "t-att-class": () => ({
                "o_wanim_overflow_xy_hidden": this.forceOverflowXYHidden || this.hasAnimationInProgress,
            }),
        },
        "_root": {
            "t-on-updatecontent.noupdate": (ev) => {
                if (ev.target.classList.contains("o_animate")) {
                    this.updateContent();
                }
            },
        },
    };

    setup() {
        this.scrollingElement = getScrollingElement(this.el.ownerDocument);
        const animatedElements = this.el.querySelectorAll(".o_animate");
        // Fix for "transform: none" not overriding keyframe transforms on
        // some iPhone using Safari. Note that all animated elements are checked
        // (not only one) as the bug is not systematic and may depend on some
        // other conditions (for example: an animated image in a block which is
        // hidden on mobile would not have the issue).
        this.forceOverflowXYHidden = [...animatedElements].some(el => {
            return window.getComputedStyle(el).transform !== "none";
        });
    }

    get hasAnimationInProgress() {
        return this.el.querySelector(".o_animating") != null;
    }
}

registry
    .category("public.interactions")
    .add("website.website_animate_overflow", WebsiteAnimateOverflow);

registry
    .category("public.interactions.edit")
    .add("website.website_animate_overflow", {
        Interaction: WebsiteAnimateOverflow,
    });
