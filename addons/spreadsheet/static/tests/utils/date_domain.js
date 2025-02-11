/** @odoo-module */

const { DateTime } = luxon;
import { Domain } from "@web/core/domain";

function getDateDomainBounds(domain) {
    const startDateStr = domain[1][2];
    const endDateStr = domain[2][2];

    const isDateTime = startDateStr.includes(":");

    if (isDateTime) {
        const dateTimeFormat = "yyyy-MM-dd HH:mm:ss";
        const start = DateTime.fromFormat(startDateStr, dateTimeFormat);
        const end = DateTime.fromFormat(endDateStr, dateTimeFormat);
        return { start, end };
    }

    const start = DateTime.fromISO(startDateStr);
    const end = DateTime.fromISO(endDateStr);
    const startIsIncluded = domain[1][1] === ">=";
    const endIsIncluded = domain[2][1] === "<=";
    return {
        start: startIsIncluded ? start.startOf("day") : start.endOf("day"),
        end: endIsIncluded ? end.endOf("day") : end.startOf("day"),
    };
}

/**
 * @param {object} assert
 * @param {string} field
 * @param {string} start
 * @param {string} end
 * @param {import("@web/core/domain").DomainRepr} domain
 */
export function assertDateDomainEqual(assert, field, start, end, domain) {
    domain = new Domain(domain).toList();
    assert.deepEqual(domain[0], "&");
    assert.deepEqual(domain[1], [field, ">=", start]);
    assert.deepEqual(domain[2], [field, "<=", end]);
}

/**
 * @param {import("@web/core/domain").DomainRepr} domain
 * @returns {number}
 */
export function getDateDomainDurationInDays(domain) {
    domain = new Domain(domain).toList();
    const bounds = getDateDomainBounds(domain);
    const diff = bounds.end.diff(bounds.start, ["days"]);
    return Math.round(diff.days);
}
