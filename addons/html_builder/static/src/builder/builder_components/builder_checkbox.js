import { Component } from "@odoo/owl";
import { CheckBox } from "@web/core/checkbox/checkbox";
import {
    clickableWeWidgetProps,
    useClickableWeWidget,
    BuilderComponent,
    useDependecyDefinition,
} from "../builder_helpers";

export class BuilderCheckbox extends Component {
    static template = "html_builder.BuilderCheckbox";
    static components = { BuilderComponent, CheckBox };
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
