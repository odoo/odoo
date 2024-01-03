/** @odoo-module */
import { formatMonetary } from "@web/views/fields/formatters";
import { roundDecimals } from "@web/core/utils/numbers";

export const formatCurrency = (value, currency, hasSymbol = true) => {
    return formatMonetary(value, {
        currencyId: currency.id,
        noSymbol: !hasSymbol,
    });
};

export const roundCurrency = (value, currency) => {
    return roundDecimals(value, currency.decimal_places);
};
