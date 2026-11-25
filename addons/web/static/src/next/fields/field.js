import { Component, t, useProps } from "@odoo/owl";
import { registry } from "@web/core/registry";

/**
 * The components that display a field, by widget name or by field type: the
 * widget of a field node wins over its type.
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
 *  widget: string | null;
 *  string: string;
 *  readonly: boolean;
 *  style: string | null;
 *  Widget: typeof Component;
 *  list?: { columns: FieldNode[] };
 * }} FieldNode
 */

/**
 * What every field component receives. `record` is a record of a store: the
 * component reads its value with `record[name]()` and writes it with
 * `record[name].set(value)`.
 */
export const fieldProps = {
    record: t.object(),
    name: t.string(),
    /** id of the input, for the label of the field */
    id: t.string().optional(),
    readonly: t.boolean().optional(false),
    node: t.object(),
};

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

    get isReadonly() {
        return this.props.readonly || this.props.node.readonly;
    }

    get classNames() {
        const { node } = this.props;
        return {
            [`o_field_${node.widget || node.type}`]: true,
            o_readonly_modifier: this.isReadonly,
        };
    }
}
