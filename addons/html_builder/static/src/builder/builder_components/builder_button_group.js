import { Component } from "@odoo/owl";
import {
    basicContainerBuilderComponentProps,
    useVisibilityObserver,
    useApplyVisibility,
    BuilderComponent,
    useSelectableComponent,
} from "./utils";

export class BuilderButtonGroup extends Component {
    static template = "html_builder.BuilderButtonGroup";
    static props = {
        ...basicContainerBuilderComponentProps,
        id: { type: String, optional: true },
        dependencies: { type: [String, Array], optional: true },
        slots: { type: Object, optional: true },
    };
    static components = { BuilderComponent };

    setup() {
        useVisibilityObserver("root", useApplyVisibility("root"));

        useSelectableComponent(this.props.id);
    }
}
