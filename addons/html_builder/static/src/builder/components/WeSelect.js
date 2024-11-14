import { Component, EventBus, useSubEnv } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { basicContainerWeWidgetProps, useWeComponent } from "../builder_helpers";

export class WeSelect extends Component {
    static template = "html_builder.WeSelect";
    static props = {
        ...basicContainerWeWidgetProps,
        label: { type: String, optional: true },
        slots: Object,
    };
    static components = {
        Dropdown,
    };
    setup() {
        useWeComponent();
        const bus = new EventBus();
        useSubEnv({
            weSelectBus: bus,
        });
    }
}
