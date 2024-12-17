import { Component } from "@odoo/owl";
import {
    basicContainerWeWidgetProps,
    useInputWeWidget,
    useWeComponent,
    WeComponent,
} from "../builder_helpers";

export class WeTextInput extends Component {
    static template = "html_builder.WeTextInput";
    static props = {
        ...basicContainerWeWidgetProps,
        placeholder: { type: String, optional: true },
    };
    static components = { WeComponent };

    setup() {
        useWeComponent();
        const { state, onChange, onInput } = useInputWeWidget();
        this.onChange = onChange;
        this.onInput = onInput;
        this.state = state;
    }
}
