/** @ts-check */

import { Component } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";

export class TextFilterValue extends Component {
    static template = "spreadsheet.TextFilterValue";
    static props = {
        label: { type: String, optional: true },
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

    translate(label) {
        // the filter label is extracted from the spreadsheet json file.
        return _t(label);
    }
}
