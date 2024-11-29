import { Component, useSubEnv } from "@odoo/owl";
import { defaultOptionComponents } from "./defaultComponents";

export class OptionsContainer extends Component {
    static template = "html_builder.OptionsContainer";
    static components = { ...defaultOptionComponents };
    static props = {
        options: { type: Array },
        editingElement: true, // HTMLElement from iframe
    };

    setup() {
        useSubEnv({
            editingElement: this.props.editingElement,
            weContext: {},
        });
    }

    get title() {
        return this.env.editingElement.dataset.name;
    }
}
