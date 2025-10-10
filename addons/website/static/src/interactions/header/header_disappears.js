import { BaseHeaderSpecial } from "@website/interactions/header/base_header_special";
import { registry } from "@web/core/registry";

export class HeaderDisappears extends BaseHeaderSpecial {
    static selector = "header.o_header_disappears:not(.o_header_sidebar)";

    setup() {
        super.setup();
        this.isAnimated = true;
    }
}

registry.category("public.interactions").add("website.header_disappears", HeaderDisappears);

registry.category("public.interactions.edit").add("website.header_disappears", {
    Interaction: HeaderDisappears,
});
