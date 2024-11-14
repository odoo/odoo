import { Component } from "@odoo/owl";
import { defaultOptionComponents } from "../defaultComponents";

export class VisibilityOption extends Component {
    static template = "html_builder.VisibilityOption";
    static components = {
        ...defaultOptionComponents,
    };
}
