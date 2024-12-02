import { HeaderStandard } from "@website/interactions/header/header_standard";
import { registry } from "@web/core/registry";

class HeaderStandardEdit extends HeaderStandard {
    adjustPosition() { }
}

registry
    .category("website.edit_active_elements")
    .add("website.header_disappears", HeaderStandardEdit);
