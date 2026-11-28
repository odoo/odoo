import { registry } from "@web/core/registry";
import { Interaction } from "@web/public/interaction";
import { getScrollingElement } from "@web/core/utils/scrolling";

export const blockHoverTransformSelector =
    ".o_block_hover:is(.o_block_hover_translate, .o_block_hover_zoom_in, .o_block_hover_zoom_out)";

export class AnimateOverflow extends Interaction {
    static selector = "#wrapwrap";
    dynamicSelectors = {
        ...this.dynamicSelectors,
        _scrollingElement: () => this.scrollingElement,
    };
    dynamicContent = {
        _scrollingElement: {
            "t-att-class": () => ({
                o_wanim_overflow_xy_hidden:
                    this.forceOverflowXYHidden || this.hasAnimationInProgress,
            }),
        },
        [blockHoverTransformSelector]: {
            "t-on-transitionstart.noUpdate": this.onBlockHoverTransitionStart,
            "t-on-transitionend.noUpdate": this.onBlockHoverTransitionEnd,
        },
        _root: {
            "t-on-updatecontent.noUpdate": (ev) => {
                if (ev.target.classList.contains("o_animate")) {
                    this.updateContent();
                }
            },
        },
    };

    setup() {
        this.scrollingElement = getScrollingElement(this.el.ownerDocument);
        this.activeBlockHoverEls = new Set(
            [...this.el.querySelectorAll(`${blockHoverTransformSelector}:hover`)].filter(
                (el) => window.getComputedStyle(el).transform !== "none"
            )
        );
        const animatedElements = this.el.querySelectorAll(".o_animate");
        // Fix for "transform: none" not overriding keyframe transforms on
        // some iPhone using Safari. Note that all animated elements are checked
        // (not only one) as the bug is not systematic and may depend on some
        // other conditions (for example: an animated image in a block which is
        // hidden on mobile would not have the issue).
        this.forceOverflowXYHidden = [...animatedElements].some(
            (el) => window.getComputedStyle(el).transform !== "none"
        );
    }

    onBlockHoverTransitionStart(event) {
        if (
            event.propertyName !== "transform" ||
            !event.target.matches(blockHoverTransformSelector)
        ) {
            return;
        }
        if (!this.activeBlockHoverEls.has(event.target)) {
            this.activeBlockHoverEls.add(event.target);
            this.updateContent();
        }
    }

    onBlockHoverTransitionEnd(event) {
        if (
            event.propertyName === "transform" &&
            event.target.matches(blockHoverTransformSelector) &&
            !event.target.matches(":hover")
        ) {
            if (this.activeBlockHoverEls.delete(event.target)) {
                this.updateContent();
            }
        }
    }

    get hasAnimationInProgress() {
        return this.el.querySelector(".o_animating") != null || this.activeBlockHoverEls.size > 0;
    }
}

registry.category("public.interactions").add("website.animate_overflow", AnimateOverflow);
