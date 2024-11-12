import { Component } from "@odoo/owl";

export class ElementToolboxContainer extends Component {
    static template = "html_builder.ElementToolboxContainer";
    static props = {
        title: String,
        slots: { type: Object, optional: true },
    };
}
