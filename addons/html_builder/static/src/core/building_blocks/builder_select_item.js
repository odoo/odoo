import { useRef } from "@web/owl2/utils";
import { Component, markup, onMounted, props, t, xml } from "@odoo/owl";
import { getActiveHotkey } from "@web/core/hotkeys/hotkey_service";
import { useActionInfo, useSelectableItemComponent } from "../utils";
import { BuilderComponent } from "./builder_component";
import { BuilderSelectableWrapperComponent } from "./builder_selectable_wrapper_component";

const builderSelectItemProps = {
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
    label: t.string().optional(),
    className: t.string().optional(),
};

export class BuilderSelectItemInternal extends Component {
    static template = "html_builder.BuilderSelectItemInternal";
    props = props({
        ...builderSelectItemProps,
        className: t.string().optional(""),
    });
    static components = { BuilderComponent };

    setup() {
        if (!this.env.selectableContext) {
            throw new Error("BuilderSelectItem must be used inside a BuilderSelect component.");
        }
        this.info = useActionInfo();
        const item = useRef("item");
        let label = "";
        const getLabel = () => {
            // todo: it's not clear why the item.el?.innerHTML is not set at in
            // some cases. We fallback on a previously set value to circumvent
            // the problem, but it should be investigated.

            label = this.props.label || (item.el ? markup(item.el.innerHTML) : "") || label || "";
            return label;
        };

        onMounted(getLabel);

        const { state, operation } = useSelectableItemComponent(this.props.id, {
            getLabel,
        });
        this.state = state;
        this.operation = operation;

        this.onFocusin = this.operation.preview;
        this.onFocusout = this.operation.revert;
    }

    onClick() {
        this.env.onSelectItem();
        this.operation.commit();
        this.removeKeydown?.();
    }
    onKeydown(ev) {
        const hotkey = getActiveHotkey(ev);
        if (hotkey === "escape") {
            this.operation.revert();
            this.removeKeydown?.();
        }
    }
    onPointerEnter() {
        this.operation.preview();
        const _onKeydown = this.onKeydown.bind(this);
        document.addEventListener("keydown", _onKeydown);
        this.removeKeydown = () => document.removeEventListener("keydown", _onKeydown);
    }
    onPointerLeave() {
        this.operation.revert();
        this.removeKeydown();
    }
}

export class BuilderSelectItem extends BuilderSelectableWrapperComponent {
    static template = xml`
        <BuilderSelectItemInternal t-props="this.forwardedProps">
            <t t-call-slot="default"/>
        </BuilderSelectItemInternal>
        `;
    static components = { BuilderSelectItemInternal };
    props = props({
        ltrRtlMapping: t.string().optional(),
        isLabelLinkedToContent: t.boolean().optional(),
        ...builderSelectItemProps,
    });
}
