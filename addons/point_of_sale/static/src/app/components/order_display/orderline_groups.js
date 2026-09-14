// @ts-check
/** @odoo-module native */

/**
 * @typedef {any} PosOrderline
 * @typedef {object} OrderlineGroup
 * @property {PosOrderline[]} lines
 * @property {number} quantity
 * @property {number} displayPrice
 * @property {string[]} lotLines
 * @property {object | undefined} location
 */

/**
 * @param {PosOrderline} line
 * @returns {string}
 */
export function orderlineGroupKey(line) {
    return JSON.stringify([
        line.product_id.id,
        line.price_unit,
        line.getDiscount(),
        line.getNote(),
        line.customer_note || "",
        line.location_id?.id ?? 0,
        line.product_id.tracking === "lot" ? [...line.packLotLines].sort() : [],
        line.attribute_value_ids.map((value) => value.id).sort((a, b) => a - b),
        line.custom_attribute_value_ids
            .map((value) => [
                value.custom_product_template_attribute_value_id?.id ?? value.id,
                value.custom_value,
            ])
            .sort((a, b) => a[0] - b[0]),
    ]);
}

/**
 * @param {PosOrderline[]} lines display-ordered lines, combo children behind their parent
 * @returns {{ lines: PosOrderline[], groupOf: Map<string, OrderlineGroup> }}
 */
export function groupOrderlines(lines) {
    /** @type {PosOrderline[]} */
    const displayed = [];
    /** @type {Map<string, OrderlineGroup>} */
    const groupOf = new Map();
    /** @type {Map<string, OrderlineGroup>} */
    const groupByKey = new Map();

    for (const line of lines) {
        if (!line.isPosGroupable()) {
            displayed.push(line);
            continue;
        }
        const key = orderlineGroupKey(line);
        let group = groupByKey.get(key);
        if (!group) {
            group = {
                lines: [],
                quantity: 0,
                displayPrice: 0,
                lotLines: [],
                location: line.location_id,
            };
            groupByKey.set(key, group);
            displayed.push(line);
        }
        group.lines.push(line);
        group.quantity += line.getQuantity();
        group.displayPrice += line.displayPrice;
        group.lotLines.push(...line.packLotLines);
    }

    for (const group of groupByKey.values()) {
        const representative =
            group.lines.find((line) => line.isSelected()) || group.lines[0];
        displayed[displayed.indexOf(group.lines[0])] = representative;
        groupOf.set(representative.uuid, group);
    }
    return { lines: displayed, groupOf };
}
