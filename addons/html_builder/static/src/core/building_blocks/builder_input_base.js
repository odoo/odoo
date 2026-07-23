import { Component, proxy, signal, t, useEffect, useProps } from "@odoo/owl";
import { useActionInfo } from "../utils";

/**
 * Props given to the builder input components that are then passed to {@link BuilderInputBase}
 * components. They must be complemented when calling a `BuilderInputBase` to add
 * the necessary required props (see {@link textInputBaseProps}).
 */
export const textInputBasePassthroughProps = {
    classes: t.string().optional(),
    disabled: t.boolean().optional(),
    inputClasses: t.string().optional(),
    placeholder: t.string().optional(),
    prefix: t.string().optional(),
    prefixIcon: t.string().optional(),
    selectTextOnFocus: t.boolean().optional(),
    style: t.string().optional(),
    title: t.string().optional(),
    tooltip: t.string().optional(),
};

/**
 * Actual props used by {@link BuilderInputBase} components.
 */
export const textInputBaseProps = {
    ...textInputBasePassthroughProps,
    commit: t.function(),
    preview: t.function(),
    slots: t.object().optional(),
    value: t.or([t.string(), t.literal(null)]).optional(),
    // Event handlers
    onChange: t.function().optional(),
    onFocus: t.function().optional(),
    onInput: t.function().optional(),
    onKeydown: t.function().optional(),
};

/**
 * @abstract
 */
export class BuilderInputBase extends Component {
    static template;

    // Ref on the input element, either owned by the parent (`inputRef` prop) or local.
    inputRef = useProps.static(
        "inputRef",
        t.signal(t.ref()).optional(() => signal.ref())
    );

    setup() {
        this.isEditing = false;
        this.info = useActionInfo(this.props);
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
}
