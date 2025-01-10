import { Component } from "@odoo/owl";
import {
    clickableBuilderComponentProps,
    BuilderComponent,
    defaultBuilderComponentProps,
    useSelectableItemComponent,
} from "./utils";

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
        className: { type: String, optional: true },

        slots: { type: Object, optional: true },
    };
    static defaultProps = defaultBuilderComponentProps;

    setup() {
        const { state, operation } = useSelectableItemComponent(this.props.id);
        this.state = state;
        this.onClick = operation.commit;
        this.onMouseenter = operation.preview;
        this.onMouseleave = operation.revert;
    }

    get className() {
        let className = this.state.isActive ? "active" : "";
        const widthClass = this.env.actionBus ? " w-auto" : " w-25";
        className += widthClass;
        if (this.props.className) {
            className = `${className} ${this.props.className}`;
        }
        if (!this.props.icon) {
            return className;
        }
        if (this.props.icon.startsWith("fa-")) {
            return className + ` fa fa-fw ${this.props.icon}`;
        } else if (this.props.icon.startsWith("oi-")) {
            return className + ` oi oi-fw ${this.props.icon}`;
        }
        return className;
    }
}
