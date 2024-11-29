const { DateTime } = luxon;
import { Domain } from "@web/core/domain";
import { expect } from "@odoo/hoot";

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
 * @param {string} field
 * @param {string} start
 * @param {string} end
 * @param {import("@web/core/domain").DomainRepr} domain
 */
export function assertDateDomainEqual(field, start, end, domain) {
    domain = new Domain(domain).toList();
    expect(domain[0]).toBe("&");
    expect(domain[1]).toEqual([field, ">=", start]);
    expect(domain[2]).toEqual([field, "<=", end]);
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
