import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

import { touching, isVisible } from "@web/core/utils/ui";

export class BottomFixedElement extends Interaction {
    static selector = "#wrapwrap";
    dynamicContent = {
        _window: {
            "t-on-resize": this.hideBottomFixedElements,
            "t-on-scroll": this.hideBottomFixedElements,
        },
    };

    destroy() {
        this.restoreBottomFixedElements();
    }

    hideBottomFixedElements() {
        // Note: check in the whole DOM instead of #wrapwrap as unfortunately
        // some things are still put outside of the #wrapwrap (like the livechat
        // button which is the main reason of this code).
        const bottomFixedEls = document.querySelectorAll(".o_bottom_fixed_element");
        if (!bottomFixedEls.length) {
            return;
        }

        // The bottom fixed elements are always hidden when a modal is open
        // thanks to the CSS that is based on the 'modal-open' class added to
        // the body. However, when the modal does not have a backdrop (e.g.
        // cookies bar), this 'modal-open' class is not added. That's why we
        // handle it here. Note that the popup widget code triggers a 'scroll'
        // event when the modal is hidden to make the bottom fixed elements
        // reappear.
        if (this.el.querySelector(".s_popup_no_backdrop.show")) {
            for (const bottomFixedEl of bottomFixedEls) {
                bottomFixedEl.classList.add("o_bottom_fixed_element_hidden");
            }
            return;
        }

        this.restoreBottomFixedElements();

        if (
            document.scrollingElement.offsetHeight + document.scrollingElement.scrollTop >=
            document.scrollingElement.scrollHeight - 2
        ) {
            const buttonEls = [...this.el.querySelectorAll("a, .btn")].filter(isVisible);
            for (const bottomFixedEl of bottomFixedEls) {
                const bcr = bottomFixedEl.getBoundingClientRect();
                const touchingButtonEl = touching(buttonEls, {
                    top: bcr.top,
                    right: bcr.right,
                    bottom: bcr.bottom,
                    left: bcr.left,
                    width: bcr.width,
                    height: bcr.height,
                    x: bcr.x,
                    y: bcr.y,
                });
                if (touchingButtonEl.length) {
                    if (bottomFixedEl.classList.contains("o_bottom_fixed_element_move_up")) {
                        bottomFixedEl.style.marginBottom =
                            window.innerHeight -
                            touchingButtonEl.getBoundingClientRect().top +
                            5 +
                            "px";
                    } else {
                        bottomFixedEl.classList.add("o_bottom_fixed_element_hidden");
                    }
                }
            }
        }
    }

    restoreBottomFixedElements() {
        const bottomFixedEls = this.el.querySelectorAll(".o_bottom_fixed_element");
        for (const bottomFixedEl of bottomFixedEls) {
            bottomFixedEl.classList.remove("o_bottom_fixed_element_hidden");
            if (bottomFixedEl.classList.contains("o_bottom_fixed_element_move_up")) {
                bottomFixedEl.style.marginBottom = "";
            }
        }
    }
}

registry.category("public.interactions").add("website.bottom_fixed_element", BottomFixedElement);

registry.category("public.interactions.edit").add("website.bottom_fixed_element", {
    Interaction: BottomFixedElement,
});
