import { Component } from "@odoo/owl";
import { defaultOptionComponents } from "../components/defaultComponents";
import { registry } from "@web/core/registry";

export class BorderOption extends Component {
    static template = "html_builder.BorderOption";
    static components = {
        ...defaultOptionComponents,
    };
}

registry.category("sidebar-element-option").add("BorderOption", {
    OptionComponent: BorderOption,
    selector: "section .row > div", // TODO to use the correct selector
});
