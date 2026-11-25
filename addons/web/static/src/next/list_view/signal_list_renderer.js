import { Component, t, useProps } from "@odoo/owl";
import { displayValue } from "../fields/display_value";

export class SignalListRenderer extends Component {
    static template = "web.SignalListRenderer";

    props = useProps({
        /** records of the store */
        records: t.array(),
        /** @type {any} see `getColumns` in the view */
        columns: t.array(),
        openRecord: t.function(),
    });

    /**
     * @param {any} record
     * @param {{ name: string; field: any }} column
     */
    displayValue(record, column) {
        return displayValue(record[column.name](), column.field);
    }
}
