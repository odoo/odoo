import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { defaultOptionComponents } from "../defaultComponents";

export class VisibilityTool extends Component {
    static template = "html_builder.VisibilityTool";
    static components = {
        ...defaultOptionComponents,
    };
}

registry.category("sidebar-element-toolbox").add("VisibilityTool", {
    ToolboxComponent: VisibilityTool,
    selector: "section, .s_hr",
});
