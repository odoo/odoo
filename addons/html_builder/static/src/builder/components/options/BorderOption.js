import { Component } from "@odoo/owl";
import { defaultOptionComponents } from "../defaultComponents";

export class BorderOption extends Component {
    static template = "html_builder.BorderOption";
    static components = {
        ...defaultOptionComponents,
    };
}
