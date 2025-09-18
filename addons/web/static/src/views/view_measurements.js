// @ts-check

/** @module @web/views/view_measurements - Computes available report measures from field definitions and active selections */

/**
 *
 * @param {Object} fields
 * @param {Object} fieldAttrs
 * @param {string[]} activeMeasures
 * @returns {Object}
 */

import { _t } from "@web/core/l10n/translation";
import { unique } from "@web/core/utils/collections/arrays";
export const computeReportMeasures = (
    fields,
    fieldAttrs,
    activeMeasures,
    { sumAggregatorOnly = false } = {},
) => {
    const measures = {
        __count: { name: "__count", string: _t("Count"), type: "integer" },
    };
    for (const [fieldName, field] of Object.entries(fields)) {
        if (fieldName === "id") {
            continue;
        }
        const { isInvisible } = fieldAttrs[fieldName] || {};
        if (isInvisible) {
            continue;
        }
        if (
            ["integer", "float", "monetary"].includes(field.type) &&
            ((sumAggregatorOnly && field.aggregator === "sum") ||
                (!sumAggregatorOnly && field.aggregator))
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

    const sortedMeasures = Object.entries(measures).sort(([m1, f1], [m2, f2]) => {
        if (m1 === "__count" || m2 === "__count") {
            return m1 === "__count" ? 1 : -1; // Count is always last
        }
        return f1.string.toLowerCase().localeCompare(f2.string.toLowerCase());
    });

    return Object.fromEntries(sortedMeasures);
};

/**
 * Given an array of values and an aggregator function, returns the aggregated
 * value.
 *
 * @param {number[]} values
 * @param {'sum'|'avg'|'min'|'max'|'count'|'count_distinct'} aggregator
 * @returns number
 * @throws {Error} if the aggregator function given isn't supported
 */
export function computeAggregatedValue(values, aggregator) {
    if (aggregator === "sum") {
        return values.reduce((acc, v) => v + acc, 0);
    } else if (aggregator === "avg") {
        return values.reduce((acc, v) => v + acc, 0) / values.length;
    } else if (aggregator === "min") {
        return Math.min(Infinity, ...values);
    } else if (aggregator === "max") {
        return Math.max(-Infinity, ...values);
    } else if (aggregator === "count") {
        return values.length;
    } else if (aggregator === "count_distinct") {
        return unique(values).length;
    }
    throw new Error(`Invalid aggregator '${aggregator}'`);
}

/**
 * In the preview implementation of reporting views, the virtual field used to
 * display the number of records was named __count__, whereas __count is
 * actually the one used in xml. So basically, activating a filter specifying
 * __count as measures crashed. Unfortunately, as __count__ was used in the JS,
 * all filters saved as favorite at that time were saved with __count__, and
 * not __count. So in order the make them still work with the new
 * implementation, we handle both __count__ and __count.
 *
 * This function replaces occurences of '__count__' by '__count' in the given
 * element(s).
 *
 * @param {any | any[]} [measure]
 * @returns {any}
 */
export function processMeasure(measure) {
    if (Array.isArray(measure)) {
        return measure.map(processMeasure);
    }
    return measure === "__count__" ? "__count" : measure;
}
