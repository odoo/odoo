import { Component } from "@odoo/owl";
import {
    useVisibilityObserver,
    useApplyVisibility,
    basicContainerWeWidgetProps,
    useWeComponent,
    WeComponent,
} from "../builder_helpers";

export class WeRow extends Component {
    static template = "html_builder.WeRow";
    static components = { WeComponent };
    static props = {
        ...basicContainerWeWidgetProps,
        label: String,
        dependencies: { type: [String, Array], optional: true },
        tooltip: { type: String, optional: true },
        slots: { type: Object, optional: true },
    };

    setup() {
        useWeComponent();
        useVisibilityObserver("content", useApplyVisibility("root"));
    }
}
