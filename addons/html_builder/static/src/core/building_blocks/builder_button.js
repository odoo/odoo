import { Component } from "@odoo/owl";
import { clickableBuilderComponentProps, useSelectableItemComponent } from "./utils";
import { BuilderComponent } from "./builder_component";

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
        classActive: { type: String, optional: true },
        style: { type: String, optional: true },
        type: { type: String, optional: true },

        slots: { type: Object, optional: true },
    };

    static defaultProps = {
        type: "primary",
    };

    setup() {
        const { state, operation } = useSelectableItemComponent(this.props.id);
        this.state = state;
        this.onClick = operation.commit;
        this.onMouseenter = operation.preview;
        this.onMouseleave = operation.revert;
    }

    get className() {
        let className = this.props.className || "";
        className += ` btn-${this.props.type}`;
        if (this.state.isActive) {
            className = `active ${className}`;
            if (this.props.classActive) {
                className += ` ${this.props.classActive}`;
            }
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
