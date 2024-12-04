import { registry } from "@web/core/registry";

registry.category("sidebar-element-option").add("AlertOption", {
    template: "html_builder.AlertOption",
    selector: ".s_alert",
    sequence: 5,
});
