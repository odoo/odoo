import { Component } from "@odoo/owl";

export class OptionsContainer extends Component {
    static template = "html_builder.OptionsContainer";
    static props = {
        slots: { type: Object, optional: true },
    };

    get title() {
        return this.env.editingElement.dataset.name;
    }
}
