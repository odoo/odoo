import { Component } from "@odoo/owl";
import {
    clickableBuilderComponentProps,
    useActionInfo,
    useSelectableItemComponent,
} from "../utils";
import { BuilderComponent } from "./builder_component";
import { Img } from "../img";

export class BuilderButton extends Component {
    static template = "html_builder.BuilderButton";
    static components = { BuilderComponent, Img };
    static props = {
        ...clickableBuilderComponentProps,

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
        type: "secondary",
    };

    setup() {
        this.info = useActionInfo();
        const { state, operation } = useSelectableItemComponent(this.props.id);
        this.state = state;
        this.onClick = operation.commit;
        this.onPointerEnter = operation.preview;
        this.onPointerLeave = operation.revert;
    }

    get className() {
        let className = this.props.className || "";
        if (this.props.type) {
            className += ` btn-${this.props.type}`;
        }
        if (this.state.isActive) {
            className = `active ${className}`;
            if (this.props.classActive) {
                className += ` ${this.props.classActive}`;
            }
        }
        if (this.props.icon) {
            className += ` o-hb-btn-has-icon`;
        }
        if (this.props.iconImg) {
            className += ` o-hb-btn-has-img-icon`;
        }
        return className;
    }

    get iconClassName() {
        if (this.props.icon.startsWith("fa-")) {
            return `fa ${this.props.icon}`;
        } else if (this.props.icon.startsWith("oi-")) {
            return `oi ${this.props.icon}`;
        }
        return "";
    }
}
