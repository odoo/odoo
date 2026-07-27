import { Component, props, proxy, signal, t, useEffect } from "@odoo/owl";
import { useActionInfo } from "../utils";

// Props given to the builder input components that are then passed to the
// BuilderInputBase.
export const textInputBasePassthroughProps = {
    action: { type: String, optional: true },
    placeholder: { type: String, optional: true },
    title: { type: String, optional: true },
    style: { type: String, optional: true },
    tooltip: { type: String, optional: true },
    classes: { type: String, optional: true },
    inputClasses: { type: String, optional: true },
    prefix: { type: String, optional: true },
    prefixIcon: { type: String, optional: true },
    selectTextOnFocus: { type: Boolean, optional: true },
    disabled: { type: Boolean, optional: true },
};

// Abstract Component
export class BuilderInputBase extends Component {
    static template = "";
    static props = {
        slots: { type: Object, optional: true },
        ...textInputBasePassthroughProps,
        commit: { type: Function },
        preview: { type: Function },
        onFocus: { type: Function, optional: true },
        onInput: { type: Function, optional: true },
        onChange: { type: Function, optional: true },
        onKeydown: { type: Function, optional: true },
        onBeforeInput: { type: Function, optional: true },
        value: { type: [String, { value: null }], optional: true },
    };

    // Ref on the input element, either owned by the parent (`inputRef` prop) or local.
    inputRef = props.static(
        "inputRef",
        t.signal(t.ref()).optional(() => signal.ref())
    );

    setup() {
        this.isEditing = false;
        this.info = useActionInfo();
        this.state = proxy({ value: this.props.value });
        useEffect(() => {
            const value = this.props.value;
            this.state.value = this.isEditing ? this.inputRef().value : value;
        });
    }

    onChange(ev) {
        this.isEditing = false;
        const normalizedDisplayValue = this.props.commit(ev.target.value);
        ev.target.value = normalizedDisplayValue;
        this.state.value = normalizedDisplayValue;
        this.props.onChange?.(ev);
    }

    onInput(ev) {
        this.isEditing = true;
        this.state.value = ev.target.value;
        this.props.preview(ev.target.value);
        this.props.onInput?.(ev);
    }

    onFocus(ev) {
        if (this.props.selectTextOnFocus) {
            this.inputRef().select();
        }
        this.props.onFocus?.(ev);
    }

    onKeydown(ev) {
        this.props.onKeydown?.(ev);
    }

    onBeforeInput(ev) {
        this.props.onBeforeInput?.(ev);
    }
}
