import { Component } from "@odoo/owl";
import {
    useVisibilityObserver,
    useApplyVisibility,
    basicContainerBuilderComponentProps,
    useBuilderComponent,
    BuilderComponent,
} from "./utils";

export class BuilderRow extends Component {
    static template = "html_builder.BuilderRow";
    static components = { BuilderComponent };
    static props = {
        ...basicContainerBuilderComponentProps,
        label: String,
        dependencies: { type: [String, Array], optional: true },
        tooltip: { type: String, optional: true },
        slots: { type: Object, optional: true },
        extraClassName: { type: String, optional: true },
    };

    setup() {
        useBuilderComponent();
        useVisibilityObserver("content", useApplyVisibility("root"));
    }
}
