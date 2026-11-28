import { Component, t, useProps } from "@odoo/owl";
import { Field } from "../fields/field";

/**
 * Records of a store as a table: one row per record, one column per field
 * node. The cells are readonly.
 *
 * It is the renderer of the list view, and the list of x2many fields.
 */
export class ListRenderer extends Component {
    static template = "web.next.ListRenderer";
    static components = { Field };

    props = useProps({
        /** records of a store */
        records: t.array(),
        /** @type {any} field nodes, see `FieldNode` */
        columns: t.array(),
        /** called with a record when its row is clicked */
        openRecord: t.function().optional(),
    });
}
