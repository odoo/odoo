import { user } from "@web/core/user";

/**
 * Aggregates to request along with the one of a field having a currency: the
 * record currencies and, for a sum, its converted counterpart.
 *
 * @param {Object} field
 * @returns {string[]}
 */
export function getCurrencyAggregateSpecs(field) {
    const specs = [`${field.currency_field}:array_agg_distinct`];
    if (field.aggregator === "sum") {
        specs.push(`${field.name}:sum_currency`);
    }
    return specs;
}

/**
 * Whether an aggregate of a group is used with regard to currency conversion:
 * the converted counterpart of a sum is only used when its group mixes
 * currencies, any other aggregate is always used.
 *
 * @param {Object} groupData
 * @param {Object} field
 * @param {string} aggregator
 * @returns {boolean}
 */
export function isConvertedAggregateUsed(groupData, field, aggregator) {
    if (aggregator === "sum_currency" && field.aggregator === "sum") {
        return groupData[`${field.currency_field}:array_agg_distinct`].length > 1;
    }
    return true;
}

/**
 * Currency in which a monetary aggregate is expressed, undefined if unknown.
 *
 * @param {Object} field
 * @param {number[]} currencyIds currencies of the aggregated records
 * @returns {number|undefined}
 */
export function getAggregateCurrencyId(field, currencyIds) {
    const multiCurrency = currencyIds.length > 1;
    if (field.aggregator?.endsWith("_currency") || (multiCurrency && field.aggregator === "sum")) {
        return user.activeCompany.currency_id;
    }
    return multiCurrency ? undefined : currencyIds[0];
}
