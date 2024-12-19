import { Component, EventBus, useSubEnv } from "@odoo/owl";
import {
    basicContainerWeWidgetProps,
    useVisibilityObserver,
    useApplyVisibility,
    useBuilderComponent,
    BuilderComponent,
} from "../builder_helpers";

export class BuilderButtonGroup extends Component {
    static template = "html_builder.BuilderButtonGroup";
    static props = {
        ...basicContainerWeWidgetProps,
        dependencies: { type: [String, Array], optional: true },
        slots: { type: Object, optional: true },
    };
    static components = { BuilderComponent };

    setup() {
        useBuilderComponent();
        const bus = new EventBus();
        useSubEnv({
            actionBus: bus,
        });
        useVisibilityObserver("root", useApplyVisibility("root"));
    }
}
