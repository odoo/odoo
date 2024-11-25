import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { defaultOptionComponents } from "../components/defaultComponents";

export class VisibilityOption extends Component {
    static template = "html_builder.VisibilityOption";
    static components = {
        ...defaultOptionComponents,
    };
}

registry.category("sidebar-element-option").add("VisibilityOption", {
    OptionComponent: VisibilityOption,
    selector: "section, .s_hr",
});
