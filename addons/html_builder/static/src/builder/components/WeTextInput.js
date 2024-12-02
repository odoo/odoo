import { Component } from "@odoo/owl";
import { basicContainerWeWidgetProps, useInputWeWidget, useWeComponent } from "../builder_helpers";

export class WeTextInput extends Component {
    static template = "html_builder.WeTextInput";
    static props = {
        ...basicContainerWeWidgetProps,
        placeholder: { type: String, optional: true },
    };

    setup() {
        useWeComponent();
        const { state, onChange, onInput } = useInputWeWidget();
        this.onChange = onChange;
        this.onInput = onInput;
        this.state = state;
    }
}
