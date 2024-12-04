import { HoverableDropdown } from "@website/interactions/dropdown/hoverable_dropdown";
import { registry } from "@web/core/registry";

const HoverableDropdownEdit = I => class extends I {
    /**
     * @param {Event} ev
     */
    onMouseEnter(ev) {
        if (this.el.querySelector(".dropdown-toggle.show")) {
            return;
        } else {
            super.onMouseEnter(ev);
        }
    }
    
    /**
     * @param {Event} ev
     */
    onMouseLeave(ev) { }
};

registry
    .category("website.editable_active_elements_builders")
    .add("website.hoverable_dropdown", {
        Interaction: HoverableDropdown,
        mixin: HoverableDropdownEdit
    });
