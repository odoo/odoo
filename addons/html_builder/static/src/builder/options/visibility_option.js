import { registry } from "@web/core/registry";

registry.category("sidebar-element-option").add("VisibilityOption", {
    template: "html_builder.VisibilityOption",
    selector: "section, .s_hr",
});
