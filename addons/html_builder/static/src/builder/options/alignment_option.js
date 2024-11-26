import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { defaultOptionComponents } from "../components/defaultComponents";

export class AlignmentOption extends Component {
    static template = "html_builder.AlignmentOption";
    static components = { ...defaultOptionComponents };
}

registry.category("sidebar-element-option").add("AlignmentOption", {
    OptionComponent: AlignmentOption,
    selector: ".s_share, .s_text_highlight, .s_social_media",
});
