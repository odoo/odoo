// @ts-check
/** @odoo-module native */

import { xml } from "@odoo/owl";
import {
    formatDate,
    formatDateTime,
    toLocaleDateString,
    toLocaleDateTimeString,
} from "@web/core/l10n/dates";
import { localization } from "@web/core/l10n/localization";
import { DateTime } from "@web/core/l10n/luxon";
import { renderToElement } from "@web/core/utils/render";

let _dateWidths = null;

/**
 * @param {"date" | "datetime" | "datetimeWithSeconds" | "numericDate" | "numericDatetime"} key
 * @returns {number | undefined}
 */
function dateWidth(key) {
    if (!_dateWidths) {
        if (!localization.dateFormat) {
            return undefined;
        }
        computeOptimalDateWidths();
    }
    return _dateWidths[key];
}

export const FIELD_WIDTHS = Object.freeze({
    boolean: [20, 100],
    char: [80],
    get date() {
        return dateWidth("date");
    },
    get datetime() {
        return dateWidth("datetime");
    },
    get datetime_seconds() {
        return dateWidth("datetimeWithSeconds");
    },
    get numeric_date() {
        return dateWidth("numericDate");
    },
    get numeric_datetime() {
        return dateWidth("numericDatetime");
    },
    float: [120, 200],
    integer: [100, 180],
    many2many: [80],
    many2one_reference: [80],
    many2one: [80],
    monetary: [140, 240],
    one2many: [80],
    reference: [80],
    selection: [80],
    text: [80, 1200],
});

export function resetDateFieldWidths() {
    _dateWidths = null;
}

/** @returns {boolean} */
function isMeridiemTimeFormat() {
    return /\ba+\b/.test(localization.timeFormat || "");
}

function computeOptimalDateWidths() {
    const values = {
        date: [],
        datetime: [],
        datetimeWithSeconds: [],
        numericDate: [],
        numericDatetime: [],
    };
    const meridiem = isMeridiemTimeFormat();
    for (let month = 1; month <= 12; month++) {
        values.date.push(toLocaleDateString(DateTime.local(2017, month, 20)));
        const hours = meridiem ? [10, 22] : [10];
        for (const hour of hours) {
            const sample = DateTime.local(2017, month, 25, hour, 0, 0);
            values.datetime.push(
                toLocaleDateTimeString(sample, {
                    showDate: true,
                    showTime: true,
                    showSeconds: false,
                }),
            );
            values.datetimeWithSeconds.push(
                toLocaleDateTimeString(sample, {
                    showDate: true,
                    showTime: true,
                    showSeconds: true,
                }),
            );
        }
    }
    values.numericDate.push(formatDate(DateTime.local(2017, 1, 1)));
    values.numericDatetime.push(formatDateTime(DateTime.local(2017, 1, 1, 10, 0, 0)));
    if (meridiem) {
        values.numericDatetime.push(
            formatDateTime(DateTime.local(2017, 1, 1, 22, 0, 0)),
        );
    }

    const template = xml`
        <div class="invisible" style="font-variant-numeric: tabular-nums;">
            <div t-foreach="Object.keys(values)" t-as="key" t-key="key" t-att-class="key">
                <div t-foreach="values[key]" t-as="value" t-key="value_index">
                    <span t-out="value"/>
                </div>
            </div>
        </div>`;
    const div = renderToElement(template, { values });
    document.body.append(div);
    _dateWidths = {};
    for (const key of Object.keys(values)) {
        const spans = div.querySelectorAll(`.${key} span`);
        const widths = [...spans].map((span) => span.getBoundingClientRect().width);
        _dateWidths[key] = Math.ceil(Math.max(...widths) * 1.05);
    }
    document.body.removeChild(div);
}
