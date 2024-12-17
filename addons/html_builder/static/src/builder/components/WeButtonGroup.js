import { Component, EventBus, useSubEnv } from "@odoo/owl";
import {
    basicContainerWeWidgetProps,
    useVisibilityObserver,
    useApplyVisibility,
    useWeComponent,
    WeComponent,
} from "../builder_helpers";

export class WeButtonGroup extends Component {
    static template = "html_builder.WeButtonGroup";
    static props = {
        ...basicContainerWeWidgetProps,
        dependencies: { type: [String, Array], optional: true },
        slots: { type: Object, optional: true },
    };
    static components = { WeComponent };

    setup() {
        useWeComponent();
        const bus = new EventBus();
        useSubEnv({
            actionBus: bus,
        });
        useVisibilityObserver("root", useApplyVisibility("root"));
    }
}
