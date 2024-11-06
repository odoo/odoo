import { registry } from "@web/core/registry";
import { Animation } from "./animation";

registry
    .category("website.edit_active_elements")
    .add("website.animation", Animation);
