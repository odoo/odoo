import { HoverableDropdown } from "@website/interactions/dropdown/hoverable_dropdown";
import { registry } from "@web/core/registry";

const HoverableDropdownEdit = (I) =>
    class extends I {
        /**
         * @param {MouseEvent} ev
         * @param {HTMLElement} currentTargetEl
         */
        onMouseEnter(ev, currentTargetEl) {
            if (this.el.querySelector(".dropdown-toggle.show")) {
                return;
            } else {
                super.onMouseEnter(ev, currentTargetEl);
            }
        }

        onMouseLeave() {}
    };

registry.category("public.interactions.edit").add("website.hoverable_dropdown", {
    Interaction: HoverableDropdown,
    mixin: HoverableDropdownEdit,
});
