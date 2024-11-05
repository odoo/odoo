import { Component, EventBus, useSubEnv } from "@odoo/owl";
import { basicContainerWeWidgetProps, useWeComponent } from "../builder_helpers";

export class ButtonGroup extends Component {
    static template = "html_builder.ButtonGroup";
    static props = {
        ...basicContainerWeWidgetProps,
        slots: { type: Object, optional: true },
    };

    setup() {
        useWeComponent();
        const bus = new EventBus();
        useSubEnv({
            buttonGroupBus: bus,
        });
    }
}
