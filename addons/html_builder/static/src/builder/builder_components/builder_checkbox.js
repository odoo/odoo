import { Component } from "@odoo/owl";
import { CheckBox } from "@web/core/checkbox/checkbox";
import {
    clickableBuilderComponentProps,
    useClickableBuilderComponent,
    BuilderComponent,
    useDependecyDefinition,
    defaultBuilderComponentProps,
} from "../builder_helpers";

export class BuilderCheckbox extends Component {
    static template = "html_builder.BuilderCheckbox";
    static components = { BuilderComponent, CheckBox };
    static props = {
        ...clickableBuilderComponentProps,
        id: { type: String, optional: true },
    };
    static defaultProps = defaultBuilderComponentProps;

    setup() {
        const { state, operation, isActive } = useClickableBuilderComponent();
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
