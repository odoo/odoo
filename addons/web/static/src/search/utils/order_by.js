/** @odoo-module */

/**
 * @typedef {Object} OrderTerm
 * @property {string} name
 * @property {boolean} asc
 */

/**
 * @param {OrderTerm[]} orderBy
 * @returns {string}
 */
export function orderByToString(orderBy) {
    return orderBy.map((o) => `${o.name} ${o.asc ? "ASC" : "DESC"}`).join(", ");
}

/**
 * @param {any} string
 * @return {OrderTerm[]}
 */
export function stringToOrderBy(string) {
    if (!string) {
        return [];
    }
    return string.split(",").map((order) => {
        const splitOrder = order.trim().split(" ");
        if (splitOrder.length === 2) {
            return {
                name: splitOrder[0],
                asc: splitOrder[1].toLowerCase() === "asc",
            };
        } else {
            return {
                name: splitOrder[0],
                asc: true,
            };
        }
    });
}
