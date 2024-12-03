import { HoverableDropdown } from "@website/interactions/dropdown/hoverable_dropdown";
import { registry } from "@web/core/registry";

class HoverableDropdownEdit extends HoverableDropdown {

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

}

registry
    .category("website.edit_active_elements")
    .add("website.hoverable_dropdown", HoverableDropdownEdit);
