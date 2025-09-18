// @ts-check

/** @module @web/fields/field_widths - Default column widths per field type for list views */

import { xml } from "@odoo/owl";
import {
    formatDate,
    formatDateTime,
    toLocaleDateString,
    toLocaleDateTimeString,
} from "@web/core/l10n/dates";
import { localization } from "@web/core/l10n/localization";
import { renderToElement } from "@web/core/utils/render";

let _dateWidths = null;

/**
 * Default min/max column widths per field type.
 *
 * - Array `[min]` or `[min, max]`: flexible column with bounds.
 * - Number: fixed width (both min and max).
 * - Getter: lazily computed from locale (date/datetime formats vary).
 */
export const FIELD_WIDTHS = Object.freeze({
    boolean: [20, 100],
    char: [80],
    get date() {
        if (!_dateWidths) {
            computeOptimalDateWidths();
        }
        return _dateWidths.date;
    },
    get datetime() {
        if (!_dateWidths) {
            computeOptimalDateWidths();
        }
        return _dateWidths.datetime;
    },
    get numeric_date() {
        if (!_dateWidths) {
            computeOptimalDateWidths();
        }
        return _dateWidths.numericDate;
    },
    get numeric_datetime() {
        if (!_dateWidths) {
            computeOptimalDateWidths();
        }
        return _dateWidths.numericDatetime;
    },
    float: 93,
    integer: 71,
    many2many: [80],
    many2one_reference: [80],
    many2one: [80],
    monetary: 105,
    one2many: [80],
    reference: [80],
    selection: [80],
    text: [80, 1200],
});

/** Reset cached date widths (useful for tests that change locale). */
export function resetDateFieldWidths() {
    _dateWidths = null;
}

/**
 * Compute ideal date and datetime widths by rendering sample values into
 * the DOM and measuring their pixel width. Results depend on locale and
 * font, so they are computed lazily and cached.
 */
function computeOptimalDateWidths() {
    const { timeFormat } = localization;
    const values = {
        date: [],
        datetime: [],
        numericDate: [],
        numericDatetime: [],
    };
    for (let month = 1; month <= 12; month++) {
        values.date.push(toLocaleDateString(luxon.DateTime.local(2017, month, 20)));
        values.datetime.push(
            toLocaleDateTimeString(luxon.DateTime.local(2017, month, 25, 10, 0, 0), {
                showSeconds: true,
            }),
        );
        if (timeFormat === "hh:mm:ss a") {
            values.datetime.push(
                toLocaleDateTimeString(
                    luxon.DateTime.local(2017, month, 25, 22, 0, 0),
                    { showSeconds: true },
                ),
            );
        }
    }
    values.numericDate.push(formatDate(luxon.DateTime.local(2017, 1, 1)));
    values.numericDatetime.push(
        formatDateTime(luxon.DateTime.local(2017, 1, 1, 10, 0, 0)),
    );
    if (timeFormat === "hh:mm:ss a") {
        values.numericDatetime.push(
            formatDateTime(luxon.DateTime.local(2017, 1, 1, 22, 0, 0)),
        );
    }

    const template = xml`
        <div class="invisible" style="font-variant-numeric: tabular-nums;">
            <div t-foreach="Object.keys(values)" t-as="key" t-key="key" t-att-class="key">
                <div t-foreach="values[key]" t-as="value" t-key="value_index">
                    <span t-esc="value"/>
                </div>
            </div>
        </div>`;
    const div = renderToElement(template, { values });
    document.body.append(div);
    _dateWidths = {};
    for (const key in values) {
        const spans = div.querySelectorAll(`.${key} span`);
        const widths = [...spans].map((span) => span.getBoundingClientRect().width);
        _dateWidths[key] = Math.ceil(Math.max(...widths) * 1.05);
    }
    document.body.removeChild(div);
}
