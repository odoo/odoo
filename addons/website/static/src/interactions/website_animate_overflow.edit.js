import { registry } from "@web/core/registry";
import { WebsiteAnimateOverflow } from "./website_animate_overflow";

registry
    .category("website.edit_active_elements")
    .add("website.website_animate_overflow", WebsiteAnimateOverflow);
