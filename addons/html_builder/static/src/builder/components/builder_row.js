import { Component } from "@odoo/owl";
import {
    useVisibilityObserver,
    useApplyVisibility,
    basicContainerWeWidgetProps,
    useBuilderComponent,
    BuilderComponent,
} from "../builder_helpers";

export class BuilderRow extends Component {
    static template = "html_builder.BuilderRow";
    static components = { BuilderComponent };
    static props = {
        ...basicContainerWeWidgetProps,
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
