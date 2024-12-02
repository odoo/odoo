import { HeaderDisappears } from "@website/interactions/header/header_disappears";
import { registry } from "@web/core/registry";

class HeaderDisappearsEdit extends HeaderDisappears {
    adjustPosition() { }
}

registry
    .category("website.edit_active_elements")
    .add("website.header_disappears", HeaderDisappearsEdit);
