/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { CharField, charField } from "@web/views/fields/char/char_field";
const { DateTime } = luxon;

export class CharFieldWithDate extends CharField {
    static template = "stock.CharFieldWithDate";
    static props = {
        ...CharField.props,
        dateField: { type: String, optional: true },
    };

    get removalDate() {
        const removalIso = this.props.record?.data?.removal_date;
        return removalIso ? DateTime.fromISO(removalIso).toFormat("MMM d, h:mm a") : "";
    }
}

export const charFieldWithDate = {
    ...charField,
    component: CharFieldWithDate,
    supportedOptions: [
        {
            label: _t("Date field"),
            name: "date_field",
            type: "string",
        },
    ],
    extractProps: ({ options }) => ({
        dateField: options.date_field,
    }),

};

registry.category("fields").add("char_field_with_date", charFieldWithDate);
