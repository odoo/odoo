import { BaseHeaderSpecial } from "@website/interactions/header/base_header_special";
import { registry } from "@web/core/registry";

export class HeaderFixed extends BaseHeaderSpecial {
    static selector = "header.o_header_fixed:not(.o_header_sidebar)";
}

registry
    .category("website.active_elements")
    .add("website.header_fixed", HeaderFixed);

registry
    .category("website.editable_active_elements_builders")
    .add("website.header_fixed", {
        Interaction: HeaderFixed,
    });
