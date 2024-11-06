import { registry } from "@web/core/registry";
import { FullScreenHeight } from "./full_screen_height";

registry
    .category("website.edit_active_elements")
    .add("website.full_screen_height", FullScreenHeight);
