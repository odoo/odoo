import { Component } from "@odoo/owl";

export class OptionsContainer extends Component {
    static template = "html_builder.OptionsContainer";
    static props = {
        title: String,
        slots: { type: Object, optional: true },
    };
}
