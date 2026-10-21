<<<<<<< d60b687b047701f0bac45f47f4dee875dea5ba3e
import { Component, proxy, signal, t, useEffect, useProps } from "@odoo/owl";
||||||| 41850d515556c47dcd5ee60fd23ea2140f69466d
import { Component, useEffect, proxy } from "@odoo/owl";
import { useForwardRefToParent } from "@web/core/utils/hooks";
=======
import { Component, onMounted, useOnChange } from "@odoo/owl";
import { useForwardRefToParent } from "@web/core/utils/hooks";
>>>>>>> 2d2bf74bddf1fef9fb95481842cdeb25c11fb7c5
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
<<<<<<< d60b687b047701f0bac45f47f4dee875dea5ba3e
        this.info = useActionInfo(this.props);
        this.state = proxy({ value: this.props.value });
        useEffect(() => {
            const value = this.props.value;
            this.state.value = this.isEditing ? this.inputRef().value : value;
        });
||||||| 41850d515556c47dcd5ee60fd23ea2140f69466d
        this.info = useActionInfo();
        this.inputRef = useForwardRefToParent("inputRef");
        this.state = proxy({ value: this.props.value });
        useEffect(() => {
            const value = this.props.value;
            this.state.value = this.isEditing ? this.inputRef.el.value : value;
        });
=======
        this.info = useActionInfo();
        this.inputRef = useForwardRefToParent("inputRef");
        const syncValue = (value) => {
            // While editing, the DOM owns the value. In particular, number
            // inputs may display transient values such as "-" even though
            // their exposed value is an empty string.
            if (!this.isEditing && this.inputRef.el) {
                this.inputRef.el.value = value ?? "";
            }
        };
        onMounted(() => syncValue(this.props.value));
        useOnChange(() => [this.props.value], syncValue, { initialRun: false });
>>>>>>> 2d2bf74bddf1fef9fb95481842cdeb25c11fb7c5
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
