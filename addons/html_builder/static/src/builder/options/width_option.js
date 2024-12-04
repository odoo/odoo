import { registry } from "@web/core/registry";

registry.category("sidebar-element-option").add("WidthOption", {
    template: "html_builder.WidthOption",
    selector: ".s_alert, .s_blockquote, .s_text_highlight",
    sequence: 10,
});
