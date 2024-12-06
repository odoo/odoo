import { Component, EventBus, useSubEnv } from "@odoo/owl";
import {
    basicContainerWeWidgetProps,
    useVisibleWithContent,
    useWeComponent,
    WeComponent,
} from "../builder_helpers";

export class WeButtonGroup extends Component {
    static template = "html_builder.WeButtonGroup";
    static props = {
        ...basicContainerWeWidgetProps,
        slots: { type: Object, optional: true },
    };
    static components = { WeComponent };

    setup() {
        useWeComponent();
        const bus = new EventBus();
        useSubEnv({
            actionBus: bus,
        });
        useVisibleWithContent("root", "root");
    }
}
