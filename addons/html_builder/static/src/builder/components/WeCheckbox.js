import { Component } from "@odoo/owl";
import { CheckBox } from "@web/core/checkbox/checkbox";
import {
    clickableWeWidgetProps,
    useClickableWeWidget,
    WeComponent,
    useDependecyDefinition,
} from "../builder_helpers";

export class WeCheckbox extends Component {
    static template = "html_builder.WeCheckbox";
    static components = { WeComponent, CheckBox };
    static props = {
        ...clickableWeWidgetProps,
        id: { type: String, optional: true },
    };

    setup() {
        const { state, operation, isActive } = useClickableWeWidget();
        if (this.props.id) {
            useDependecyDefinition({ id: this.props.id, isActive });
        }
        this.state = state;
        this.onChange = operation.commit;
    }

    getClassName() {
        return "o_field_boolean o_boolean_toggle form-switch" + (this.props.extraClassName || "");
    }
}
