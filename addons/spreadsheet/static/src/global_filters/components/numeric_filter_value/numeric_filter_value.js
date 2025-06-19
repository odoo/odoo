/** @ts-check */

import { Component } from "@odoo/owl";

export class NumericFilterValue extends Component {
    static template = "spreadsheet.NumericFilterValue";
    static props = {
        onValueChanged: Function,
        value: { type: Number, optional: true },
    };
}
