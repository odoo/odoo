import { HeaderFadeOut } from "@website/interactions/header/header_fade_out";
import { registry } from "@web/core/registry";

class HeaderFadeOutEdit extends HeaderFadeOut {
    adjustPosition() { }
}

registry
    .category("website.edit_active_elements")
    .add("website.header_disappears", HeaderFadeOutEdit);
