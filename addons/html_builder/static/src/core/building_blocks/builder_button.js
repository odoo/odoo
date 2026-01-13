import { Component, xml } from "@odoo/owl";
import {
    clickableBuilderComponentProps,
    useActionInfo,
    useSelectableItemComponent,
} from "../utils";
import { BuilderComponent } from "./builder_component";
import { BuilderSelectableWrapperComponent } from "./builder_selectable_wrapper_component";
import { Image } from "../img";

const builderButtonProps = {
    ...clickableBuilderComponentProps,
    title: { type: String, optional: true },
    titleActive: { type: String, optional: true },
    label: { type: String, optional: true },
    iconImg: { type: String, optional: true },
    iconImgAlt: { type: String, optional: true },
    iconImgStyle: { type: String, optional: true },
    icon: { type: String, optional: true },
    className: { type: String, optional: true },
    classActive: { type: String, optional: true },
    style: { type: String, optional: true },
    type: { type: String, optional: true },

    slots: { type: Object, optional: true },
};

export class BuilderButtonInternal extends Component {
    static template = "html_builder.BuilderButtonInternal";
    static components = { BuilderComponent, Image };
    static props = { ...builderButtonProps };

    static defaultProps = {
        type: "secondary",
        titleActive: "",
        iconImgStyle: "",
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

export class BuilderButton extends BuilderSelectableWrapperComponent {
    static template = xml`
        <BuilderButtonInternal t-props="this.forwardedProps">
            <t t-slot="default"/>
        </BuilderButtonInternal>
        `;
    static components = { BuilderButtonInternal };
    static props = {
        ltrRtlMapping: { type: String, optional: true },
        isLabelLinkedToContent: { type: Boolean, optional: true },
        slots: { type: Object, optional: true },
        ...builderButtonProps,
    };

    get forwardedProps() {
        return {
            ...super.forwardedProps,
            iconImgStyle: this.iconImgStyle,
        };
    }

    get iconImgStyle() {
        let iconImgStyle = this.props.iconImgStyle || "";
        if (this.props.ltrRtlMapping && this.props.iconImg) {
            const shouldMirrorIcon = this.props.isLabelLinkedToContent
                ? this.env.langDir.content !== this.env.langDir.builder
                : this.env.langDir.builder === "rtl";
            if (shouldMirrorIcon) {
                iconImgStyle = `transform: scaleX(-1); ${iconImgStyle}`;
            }
        }
        return iconImgStyle;
    }
}
