import { Component, useProps } from "@odoo/owl";
import { CheckBox } from "@web/core/checkbox/checkbox";
import {
    clickableBuilderComponentProps,
    useActionInfo,
    useClickableBuilderComponent,
    useDependencyDefinition,
    useBuilderControl,
    useDomState,
} from "../utils";
import { BuilderComponent } from "./builder_component";

export class BuilderCheckbox extends Component {
    static template = "html_builder.BuilderCheckbox";
    static components = { BuilderComponent, CheckBox };

    props = useProps(clickableBuilderComponentProps);

    setup() {
        this.info = useActionInfo(this.props);
        const { operation, isApplied, onReady, reload } = useClickableBuilderComponent(this.props);
        useBuilderControl({
            kind: "toggle",
            isActive: () => this.state.isActive,
            commit: operation.commit,
            reload,
        });
        if (this.props.id) {
            useDependencyDefinition(this.props, { isActive: isApplied }, { onReady });
        }
        this.state = useDomState(async () => {
            await onReady?.();
            return {
                isActive: isApplied(),
            };
        });
        this.onPointerEnter = operation.preview;
        this.onPointerLeave = operation.revert;
        this.onChange = operation.commit;
    }

    getClassName() {
        return "o_hb_checkbox o_field_boolean o_boolean_toggle form-switch";
    }
}
