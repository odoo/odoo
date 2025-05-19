/** @ts-check */

import { Component } from "@odoo/owl";

export class TextFilterValue extends Component {
    static template = "spreadsheet.TextFilterValue";
    static props = {
        onValueChanged: Function,
        value: { type: String, optional: true },
        options: {
            type: Array,
            element: {
                type: Object,
                shape: { value: String, formattedValue: String },
                optional: true,
            },
        },
    };
}
