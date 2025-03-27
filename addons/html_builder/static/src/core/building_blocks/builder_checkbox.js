import { Component } from "@odoo/owl";
import { CheckBox } from "@web/core/checkbox/checkbox";
import {
    clickableBuilderComponentProps,
    useActionInfo,
    useClickableBuilderComponent,
    useDependencyDefinition,
    useDomState,
} from "../utils";
import { BuilderComponent } from "./builder_component";

export class BuilderCheckbox extends Component {
    static template = "html_builder.BuilderCheckbox";
    static components = { BuilderComponent, CheckBox };
    static props = {
        ...clickableBuilderComponentProps,
        id: { type: String, optional: true },
    };

    setup() {
        this.info = useActionInfo();
        const { operation, isApplied, onReady } = useClickableBuilderComponent();
        if (this.props.id) {
            useDependencyDefinition(this.props.id, { isActive: isApplied });
        }
        this.state = useDomState(
            () => ({
                isActive: isApplied(),
            }),
            { onReady }
        );
        this.onChange = operation.commit;
    }

    getClassName() {
        return "o_field_boolean o_boolean_toggle form-switch";
    }
}
