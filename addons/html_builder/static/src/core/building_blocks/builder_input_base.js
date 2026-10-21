import { Component, onMounted, signal, t, useOnChange, useProps } from "@odoo/owl";
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
        const syncValue = (value) => {
            // While editing, the DOM owns the value. In particular, number
            // inputs may display transient values such as "-" even though
            // their exposed value is an empty string.
            if (!this.isEditing && this.inputRef()) {
                this.inputRef().value = value ?? "";
            }
        };
        onMounted(() => syncValue(this.props.value));
        useOnChange(() => [this.props.value], syncValue, { initialRun: false });
    }

    onChange(ev) {
        this.isEditing = false;
        const normalizedDisplayValue = this.props.commit(ev.target.value);
        ev.target.value = normalizedDisplayValue;
        this.props.onChange?.(ev);
    }

    onInput(ev) {
        this.isEditing = true;
        this.props.preview(ev.target.value);
        this.props.onInput?.(ev);
    }

    onFocus(ev) {
        if (this.props.selectTextOnFocus) {
            this.inputRef().select();
        }
        this.props.onFocus?.(ev);
    }

    onBlur() {
        this.isEditing = false;
    }

    onKeydown(ev) {
        this.props.onKeydown?.(ev);
    }
}
