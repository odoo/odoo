import { registry } from "@web/core/registry";

registry.category("sidebar-element-option").add("BorderOption", {
    template: "html_builder.BorderOption",
    selector: "section .row > div", // TODO to use the correct selector
});
