import { HeaderFixed } from "@website/interactions/header/header_fixed";
import { registry } from "@web/core/registry";

class HeaderFixedEdit extends HeaderFixed {
    adjustPosition() { }
}

registry
    .category("website.edit_active_elements")
    .add("website.header_disappears", HeaderFixedEdit);
