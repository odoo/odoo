/**
 * Return the currency cleaned from useless info and from the `code` field to be used to generate
 * a default currency format.
 *
 * @param {object} currency
 * @returns {object}
 */
export function createDefaultCurrency(currency) {
    if (!currency) {
        return undefined;
    }
    return {
        symbol: currency.symbol,
        position: currency.position,
        decimalPlaces: currency.decimalPlaces,
    };
}
