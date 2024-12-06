import { Component, useSubEnv } from "@odoo/owl";
import { defaultOptionComponents } from "./defaultComponents";
import { useVisibleWithContent } from "../builder_helpers";

export class OptionsContainer extends Component {
    static template = "html_builder.OptionsContainer";
    static components = { ...defaultOptionComponents };
    static props = {
        options: { type: Array },
        editingElement: true, // HTMLElement from iframe
    };

    setup() {
        useSubEnv({
            getEditingElement: () => this.props.editingElement,
            weContext: {},
        });
        useVisibleWithContent("root", "content");
    }

    get title() {
        return this.env.getEditingElement().dataset.name;
    }
}
