import { Component } from "@odoo/owl";
import { useForwardRefToParent } from "@web/core/utils/hooks";

// Props given to the builder input components that are then passed to the
// BuilderTextInputBase.
export const textInputBasePassthroughProps = {
    action: { type: String, optional: true },
    placeholder: { type: String, optional: true },
    title: { type: String, optional: true },
    style: { type: String, optional: true },
    tooltip: { type: String, optional: true },
    inputClasses: { type: String, optional: true },
};

export class BuilderTextInputBase extends Component {
    static template = "html_builder.BuilderTextInputBase";
    static props = {
        slots: { type: Object, optional: true },
        inputRef: { type: Function, optional: true },
        ...textInputBasePassthroughProps,
        commit: { type: Function },
        preview: { type: Function },
        onFocus: { type: Function, optional: true },
        onKeydown: { type: Function, optional: true },
        value: { type: [String, { value: null }], optional: true },
    };

    setup() {
        this.inputRef = useForwardRefToParent("inputRef");
    }

    onChange(ev) {
        const normalizedDisplayValue = this.props.commit(ev.target.value);
        ev.target.value = normalizedDisplayValue;
    }

    onInput(ev) {
        this.props.preview(ev.target.value);
    }

    onFocus(ev) {
        this.props.onFocus?.(ev);
    }

    onKeydown(ev) {
        this.props.onKeydown?.(ev);
    }
}
