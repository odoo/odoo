import { Component, EventBus, useSubEnv } from "@odoo/owl";
import {
    basicContainerBuilderComponentProps,
    useVisibilityObserver,
    useApplyVisibility,
    useBuilderComponent,
    BuilderComponent,
} from "./utils";

export class BuilderButtonGroup extends Component {
    static template = "html_builder.BuilderButtonGroup";
    static props = {
        ...basicContainerBuilderComponentProps,
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
