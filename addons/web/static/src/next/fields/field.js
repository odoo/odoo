import { Component, t, useProps } from "@odoo/owl";
import { registry } from "@web/core/registry";

/**
 * @import { ResolveProps, StripBrands } from "@odoo/owl"
 * @import { FieldSignal } from "../store/fields"
 */

/**
 * The components that display a field, by widget name or by field type: the
 * widget of a field node wins over its type, and a field whose widget and type
 * are both unknown is displayed as text (see `FallbackField`).
 */
export const fieldRegistry = registry.category("next_fields");

/**
 * A field of an arch, as the arch parser describes it.
 *
 * @typedef {{
 *  id: string;
 *  name: string;
 *  type: string;
 *  relation: string | null;
 *  field: Record<string, any>;
 *  widget: string | null;
 *  string: string;
 *  readonly: boolean;
 *  className: string | null;
 *  style: string | null;
 *  Widget: typeof Component;
 *  list?: { columns: FieldNode[] };
 * }} FieldNode
 */

/**
 * What every field component receives, see `useField`.
 */
const fieldProps = {
    /** a record of a store */
    record: t.object(),
    name: t.string(),
    /** id of the input, for the label of the field */
    id: t.string().optional(),
    readonly: t.boolean().optional(false),
    /** @type {any} a {@link FieldNode} */
    node: t.object(),
};

/**
 * Declares the props of a field component, and returns the field: its
 * `record`, `name`, `id`, `readonly` and `node`, and its `value`: call
 * `value()` to read it, `value.set(newValue)` to write it. All of them follow
 * the props: they give the record and the field the component has now.
 *
 * The type of the value is given as an Owl type, as for `useConfig`:
 *
 *     class CharField extends Component {
 *         static template = xml`<input t-att-value="this.field.value()"/>`;
 *         field = useField(t.string()); // field.value(): string
 *     }
 *
 * @template T
 * @param {T} _type the Owl type of the value. It only types the field: the
 *  value is not checked against it.
 * @returns {ResolveProps<typeof fieldProps> & { value: FieldSignal<StripBrands<T>> }}
 */
export function useField(_type) {
    // the props are read through signals, so the field is the props object
    // itself, plus the value
    const props = useProps(fieldProps);
    const value = Object.assign(() => props.record[props.name](), {
        /** @param {any} newValue */
        set: (newValue) => props.record[props.name].set(newValue),
    });
    return Object.assign(props, { value });
}

/**
 * A field of a record, as a view displays it: a `div` named after the field,
 * around the component of the field.
 */
export class Field extends Component {
    static template = "web.next.Field";

    props = useProps({
        record: t.object(),
        /** @type {any} a {@link FieldNode} */
        node: t.object(),
        id: t.string().optional(),
        /** a readonly view, such as a list, makes all its fields readonly */
        readonly: t.boolean().optional(false),
    });

    isReadonly() {
        return this.props.readonly || this.props.node.readonly;
    }

    classNames() {
        const { node } = this.props;
        return {
            [`o_field_${node.widget || node.type}`]: true,
            o_readonly_modifier: this.isReadonly(),
            ...(node.className && { [node.className]: true }),
        };
    }
}
