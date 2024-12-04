import { registry } from "@web/core/registry";

registry.category("sidebar-element-option").add("SizeOption", {
    template: "html_builder.SizeOption",
    selector: ".s_alert",
    sequence: 20,
});
