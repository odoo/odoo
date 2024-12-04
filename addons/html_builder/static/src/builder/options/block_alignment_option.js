import { registry } from "@web/core/registry";

registry.category("sidebar-element-option").add("BlockAlignmentOption", {
    template: "html_builder.BlockAlignmentOption",
    selector: ".s_alert, .s_blockquote, .s_text_highlight",
    sequence: 30,
});
