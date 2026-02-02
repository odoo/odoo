import { Component, markup, onMounted, useRef, onPatched } from "@odoo/owl";
import { getActiveHotkey } from "@web/core/hotkeys/hotkey_service";
import {
    clickableBuilderComponentProps,
    useActionInfo,
    useSelectableItemComponent,
} from "../utils";
import { BuilderComponent } from "./builder_component";

export class BuilderSelectItem extends Component {
    static template = "html_builder.BuilderSelectItem";
    static props = {
        ...clickableBuilderComponentProps,
        title: { type: String, optional: true },
        label: { type: String, optional: true },
        className: { type: String, optional: true },
        slots: { type: Object, optional: true },
    };
    static defaultProps = {
        className: "",
    };
    static components = { BuilderComponent };

    setup() {
        if (!this.env.selectableContext) {
            throw new Error("BuilderSelectItem must be used inside a BuilderSelect component.");
        }
        this.info = useActionInfo();
        const item = useRef("item");
        let label = "";
        this.getLabel = () => {
            // todo: it's not clear why the item.el?.innerHTML is not set at in
            // some cases. We fallback on a previously set value to circumvent
            // the problem, but it should be investigated.

            label = this.props.label || (item.el ? markup(item.el.innerHTML) : "") || label || "";
            return label;
        };

        onMounted(this.getLabel);

        const { state, operation } = useSelectableItemComponent(this.props.id, {
            getLabel: this.getLabel,
        });
        this.state = state;
        this.operation = operation;

        this.onFocusin = this.operation.preview;
        this.onFocusout = this.operation.revert;
        onPatched(() => {
            this.env.throttledDropdownUpdate();
        });
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
