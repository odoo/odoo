import { Component } from "@odoo/owl";
import { CheckBox } from "@web/core/checkbox/checkbox";
import {
    clickableBuilderComponentProps,
    useClickableBuilderComponent,
    BuilderComponent,
    useDependencyDefinition,
    defaultBuilderComponentProps,
    useDomState,
} from "./utils";

export class BuilderCheckbox extends Component {
    static template = "html_builder.BuilderCheckbox";
    static components = { BuilderComponent, CheckBox };
    static props = {
        ...clickableBuilderComponentProps,
        id: { type: String, optional: true },
    };
    static defaultProps = defaultBuilderComponentProps;

    setup() {
        const { operation, isApplied } = useClickableBuilderComponent();
        if (this.props.id) {
            useDependencyDefinition(this.props.id, { isActive: isApplied });
        }
        this.state = useDomState(() => ({
            isActive: isApplied(),
        }));
        this.onChange = operation.commit;
    }

    getClassName() {
        return "o_field_boolean o_boolean_toggle form-switch" + (this.props.extraClassName || "");
    }
}
