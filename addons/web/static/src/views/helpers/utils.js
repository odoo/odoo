/** @odoo-module **/
import { _t } from "@web/core/l10n/translation";
/**
 * Parse the arch to check if is true or false
 * If the string is empyt, 0, False or false it's considered as false
 * The rest is considered as true
 *
 * @param {string} str
 * @returns {boolean}
 */
export function archParseBoolean(str) {
    return str !== "False" && str !== "false" && str !== "0" && str !== "";
}

export function computeReportMeasures(fields, fieldAttrs, activeMeasures, additionalMeasures = []) {
    const measures = {
        __count: { name: "__count", string: _t("Count"), type: "integer" },
    };
    for (const [fieldName, field] of Object.entries(fields)) {
        if (fieldName === "id" || !field.store) {
            continue;
        }
        const { isInvisible } = fieldAttrs[fieldName] || {};
        if (isInvisible && !additionalMeasures.includes(fieldName)) {
            continue;
        }
        if (
            ["integer", "float", "monetary"].includes(field.type) ||
            additionalMeasures.includes(fieldName)
        ) {
            measures[fieldName] = field;
        }
    }

    // add active measures to the measure list.  This is very rarely
    // necessary, but it can be useful if one is working with a
    // functional field non stored, but in a model with an overridden
    // read_group method.  In this case, the pivot view could work, and
    // the measure should be allowed.  However, be careful if you define
    // a measure in your pivot view: non stored functional fields will
    // probably not work (their aggregate will always be 0).
    for (const measure of activeMeasures) {
        if (!measures[measure]) {
            measures[measure] = fields[measure];
        }
    }

    for (const fieldName in fieldAttrs) {
        if (fieldAttrs[fieldName].string && fieldName in measures) {
            measures[fieldName].string = fieldAttrs[fieldName].string;
        }
    }

    const sortedMeasures = Object.entries(measures).sort(
        ([m1, { string: s1 }], [m2, { string: s2 }]) => {
            if (m1 === "__count" || m2 === "__count") {
                return m1 === "__count" ? 1 : -1; // Count is always last
            }
            return s1.toLowerCase().localeCompare(s2.toLowerCase());
        }
    );

    return Object.fromEntries(sortedMeasures);
}
