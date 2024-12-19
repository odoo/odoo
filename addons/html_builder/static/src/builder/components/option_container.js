import { Component, useSubEnv } from "@odoo/owl";
import { defaultBuilderComponents } from "../builder_components/default_builder_components";
import { useVisibilityObserver, useApplyVisibility } from "../builder_helpers";
import { DependencyManager } from "../plugins/dependency_manager";

export class OptionsContainer extends Component {
    static template = "html_builder.OptionsContainer";
    static components = { ...defaultBuilderComponents };
    static props = {
        options: { type: Array },
        editingElement: true, // HTMLElement from iframe
    };

    setup() {
        useSubEnv({
            dependencyManager: new DependencyManager(),
            getEditingElement: () => this.props.editingElement,
            getEditingElements: () => [this.props.editingElement],
            weContext: {},
        });
        useVisibilityObserver("content", useApplyVisibility("root"));
    }

    get title() {
        return this.env.getEditingElement().dataset.name;
    }
}
