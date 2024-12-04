import { BaseHeaderSpecial } from "@website/interactions/header/base_header_special";
import { registry } from "@web/core/registry";

export class HeaderDisappears extends BaseHeaderSpecial {
    static selector = "header.o_header_disappears:not(.o_header_sidebar)";

    setup() {
        super.setup();
        this.isAnimated = true;
    }
}

registry
    .category("website.active_elements")
    .add("website.header_disappears", HeaderDisappears);

registry
    .category("website.editable_active_elements_builders")
    .add("website.header_disappears", {
        Interaction: HeaderDisappears,
    });
