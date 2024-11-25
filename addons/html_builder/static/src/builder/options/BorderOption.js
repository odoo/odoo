import { Component } from "@odoo/owl";
import { defaultOptionComponents } from "../components/defaultComponents";

export class BorderOption extends Component {
    static template = "html_builder.BorderOption";
    static components = {
        ...defaultOptionComponents,
    };
}
