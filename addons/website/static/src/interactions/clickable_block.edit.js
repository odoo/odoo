import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

export class ClickableBlockEdit extends Interaction {
    static selector = ".stretched-link";
    dynamicContent = {
        _root: { "t-att-class": () => ({ "d-none": true }) },
    };
}

registry.category("public.interactions.edit").add("website.clickable_block_edit", {
    Interaction: ClickableBlockEdit,
});
