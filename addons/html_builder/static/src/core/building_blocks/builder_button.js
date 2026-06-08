import { Component, xml, props, t } from "@odoo/owl";
import { useActionInfo, useSelectableItemComponent } from "../utils";
import { BuilderComponent } from "./builder_component";
import { BuilderSelectableWrapperComponent } from "./builder_selectable_wrapper_component";
import { Image } from "../img";

const builderButtonProps = {
    // clickableBuilderComponentProps (converted inline)
    id: t.string().optional(),
    applyTo: t.string().optional(),
    preview: t.boolean().optional(),
    inheritedActions: t.array(t.string()).optional(),

    action: t.string().optional(),
    actionParam: t.any().optional(),

    // Shorthand actions.
    classAction: t.any().optional(),
    attributeAction: t.any().optional(),
    dataAttributeAction: t.any().optional(),
    styleAction: t.any().optional(),

    inverseAction: t.boolean().optional(),

    actionValue: t
        .or([
            t.boolean(),
            t.string(),
            t.number(),
            t.literal(null),
            t.array(t.or([t.boolean(), t.string(), t.number()])),
        ])
        .optional(),

    // Shorthand actions values.
    classActionValue: t.or([t.string(), t.array(), t.literal(null)]).optional(),
    attributeActionValue: t.or([t.string(), t.array(), t.literal(null)]).optional(),
    dataAttributeActionValue: t.or([t.string(), t.array(), t.literal(null)]).optional(),
    styleActionValue: t.or([t.string(), t.array(), t.literal(null)]).optional(),

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

    slots: t.object().optional(),
};

export class BuilderButtonInternal extends Component {
    static template = "html_builder.BuilderButtonInternal";
    static components = { BuilderComponent, Image };
    props = props({
        ...builderButtonProps,
        type: t.string().optional("secondary"),
        titleActive: t.string().optional(""),
        iconImgStyle: t.string().optional(""),
    });

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
            <t t-call-slot="default"/>
        </BuilderButtonInternal>
        `;
    static components = { BuilderButtonInternal };
    props = props({
        ltrRtlMapping: t.string().optional(),
        isLabelLinkedToContent: t.boolean().optional(),
        slots: t.object().optional(),
        ...builderButtonProps,
    });

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
