import { Component, t, useProps, xml } from "@odoo/owl";
import { Image } from "../img";
import {
    clickableBuilderComponentProps,
    useActionInfo,
    useSelectableItemComponent,
} from "../utils";
import { BuilderComponent } from "./builder_component";
import { BuilderSelectableWrapperComponent } from "./builder_selectable_wrapper_component";

const builderButtonProps = {
    ...clickableBuilderComponentProps,
    title: t.string().optional(),
    titleActive: t.string().optional(),
    label: t.string().optional(),
    iconImg: t.string().optional(),
    iconImgAlt: t.string().optional(),
    iconImgStyle: t.string().optional(),
    icon: t.string().optional(),
    className: t.string().optional(),
    classActive: t.string().optional(),
    style: t.string().optional(),
    type: t.string().optional(),
};

export class BuilderButtonInternal extends Component {
    static template = "html_builder.BuilderButtonInternal";
    static components = { BuilderComponent, Image };

    props = useProps({
        ...builderButtonProps,
        type: t.string().optional("secondary"),
        titleActive: t.string().optional(""),
        iconImgStyle: t.string().optional(""),
    });

    setup() {
        this.info = useActionInfo(this.props);
        const { state, operation } = useSelectableItemComponent(this.props);
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
            <t t-call-slot="default"/>
        </BuilderButtonInternal>
        `;
    static components = { BuilderButtonInternal };

    props = useProps(builderButtonProps);

    get forwardedProps() {
        return {
            ...super.forwardedProps,
            iconImgStyle: this.iconImgStyle,
        };
    }

    get iconImgStyle() {
        let iconImgStyle = this.props.iconImgStyle || "";
        if (this.selectableProps.ltrRtlMapping && this.props.iconImg) {
            const shouldMirrorIcon = this.selectableProps.isLabelLinkedToContent
                ? this.env.langDir.content !== this.env.langDir.builder
                : this.env.langDir.builder === "rtl";
            if (shouldMirrorIcon) {
                iconImgStyle = `transform: scaleX(-1); ${iconImgStyle}`;
            }
        }
        return iconImgStyle;
    }
}
