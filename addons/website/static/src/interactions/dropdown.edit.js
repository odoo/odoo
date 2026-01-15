import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

export class DropdownEdit extends Interaction {
    static selector = "[data-bs-toggle=dropdown]";
    dynamicContent = {
        _root: {
            // We want dropdown menus not to close when clicking inside them in
            // edit mode.
            "t-att-data-bs-auto-close": () => "outside",
            "t-on-hidden.bs.dropdown": () => {
                const selection = this.el.ownerDocument.getSelection();
                if (
                    this.el.parentElement
                        ?.querySelector(".dropdown-menu")
                        ?.contains(selection.anchorNode)
                ) {
                    // If the selection is in a closed dropdown, we remove it so
                    // that overlays appearing around the selection go away
                    // (like toolbar, or link tools)
                    selection.empty();
                }
            },
        },
    };
}

registry.category("public.interactions.edit").add("website.dropdown_edit", {
    Interaction: DropdownEdit,
});
