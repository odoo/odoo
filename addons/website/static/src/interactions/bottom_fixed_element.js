/** @odoo-module native */
import { makeLogger } from "@web/core/debug/debug_logger";
import { registry } from "@web/core/registry";
import { isVisible, touching } from "@web/core/utils/dom/ui";
import { Interaction } from "@web/public/interaction";

const log = makeLogger("website.interaction.bottom_fixed_element");

export class BottomFixedElement extends Interaction {
    static selector = "#wrapwrap";
    dynamicContent = {
        _window: {
            "t-on-resize": this.throttled(this.hideBottomFixedElements),
            "t-on-scroll": this.throttled(this.hideBottomFixedElements),
        },
    };

    destroy() {
        log.lifecycle("BottomFixedElement destroy: restore elements", () => ({
            elements: this.el.querySelectorAll(".o_bottom_fixed_element").length,
        }));
        this.restoreBottomFixedElements();
    }

    hideBottomFixedElements() {
        const bottomFixedEls = document.querySelectorAll(".o_bottom_fixed_element");
        if (!bottomFixedEls.length) {
            return;
        }

        if (this.el.querySelector(".s_popup_no_backdrop.show")) {
            for (const bottomFixedEl of bottomFixedEls) {
                bottomFixedEl.classList.add("o_bottom_fixed_element_hidden");
            }
            return;
        }

        this.restoreBottomFixedElements();

        if (
            document.scrollingElement.offsetHeight +
                document.scrollingElement.scrollTop >=
            document.scrollingElement.scrollHeight - 2
        ) {
            const buttonEls = [...this.el.querySelectorAll("a, .btn")].filter(
                isVisible,
            );
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
                    if (
                        bottomFixedEl.classList.contains(
                            "o_bottom_fixed_element_move_up",
                        )
                    ) {
                        bottomFixedEl.style.marginBottom =
                            window.innerHeight -
                            touchingButtonEl[0].getBoundingClientRect().top +
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

registry
    .category("public.interactions")
    .add("website.bottom_fixed_element", BottomFixedElement);

registry.category("public.interactions.edit").add("website.bottom_fixed_element", {
    Interaction: BottomFixedElement,
});
