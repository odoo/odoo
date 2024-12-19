import { Component } from "@odoo/owl";
import {
    clickableBuilderComponentProps,
    useClickableBuilderComponent,
    BuilderComponent,
    useDependencyDefinition,
    defaultBuilderComponentProps,
} from "../builder_helpers";

export class BuilderButton extends Component {
    static template = "html_builder.BuilderButton";
    static components = { BuilderComponent };
    static props = {
        ...clickableBuilderComponentProps,

        id: { type: String, optional: true },
        title: { type: String, optional: true },
        label: { type: String, optional: true },
        iconImg: { type: String, optional: true },
        iconImgAlt: { type: String, optional: true },
        icon: { type: String, optional: true },

        slots: { type: Object, optional: true },
    };
    static defaultProps = defaultBuilderComponentProps;

    setup() {
        const { state, operation, isActive, getActions } = useClickableBuilderComponent();
        if (this.props.id) {
            useDependencyDefinition({
                id: this.props.id,
                isActive,
                getActions,
                bus: this.env.actionBus,
            });
        }
        this.state = state;
        this.onClick = operation.commit;
        this.onMouseenter = operation.preview;
        this.onMouseleave = operation.revert;
    }

    get className() {
        if (!this.props.icon) {
            return "";
        }
        if (this.props.icon.startsWith("fa-")) {
            return `fa fa-fw ${this.props.icon}`;
        } else if (this.props.icon.startsWith("oi-")) {
            return `oi oi-fw ${this.props.icon}`;
        }
        return "";
    }
}
