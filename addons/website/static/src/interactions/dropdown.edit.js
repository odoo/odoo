import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

export class DropdownEdit extends Interaction {
    static selector = "[data-bs-toggle=dropdown]";
    dynamicContent = {
        _root: {
            // We want dropdown menus not to close when clicking inside them in
            // edit mode.
            "t-att-data-bs-auto-close": () => "outside",
        },
    };
}

registry.category("public.interactions.edit").add("website.dropdown_edit", {
    Interaction: DropdownEdit,
});
